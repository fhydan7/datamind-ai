import io
import math
import os
import json
import httpx
import numpy as np
import pandas as pd
from scipy import stats
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="DataMind AI Analytics", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=[v.strip() for v in os.getenv("ALLOWED_ORIGINS","http://localhost:3000").split(",")], allow_methods=["GET","POST"], allow_headers=["Authorization","Content-Type"])
URL = os.getenv("SUPABASE_URL","").rstrip("/")
KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY","")
MAX = 10*1024*1024

async def auth(authorization: str | None=Header(default=None)):
    if not URL or not KEY:
        raise HTTPException(503,"Authentication is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401,"Sign in required")
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(URL+"/auth/v1/user",headers={"apikey":KEY,"Authorization":authorization})
        if response.status_code!=200 or not response.json().get("id"):
            raise HTTPException(401,"Invalid or expired session")
        return response.json()["id"]
    except httpx.RequestError:
        raise HTTPException(502,"Authentication provider unavailable")

def num(x):
    try:
        y=float(x)
        return round(y,5) if math.isfinite(y) else None
    except (ValueError, TypeError):
        return None

@app.get("/health")
def health():
    return {"status":"ok","service":"datamind-ai"}

@app.post("/analyze")
async def analyze(file: UploadFile=File(...), user: str=Depends(auth)):
    name=(file.filename or "").lower()
    if not name.endswith((".csv",".xlsx",".xls")):
        raise HTTPException(400,"Upload a CSV or Excel file")
    payload=await file.read(MAX+1)
    if len(payload)>MAX:
        raise HTTPException(413,"File exceeds 10 MB")
    try:
        if name.endswith(".csv"):
            df=pd.read_csv(io.BytesIO(payload))
        else:
            df=pd.read_excel(io.BytesIO(payload))
    except Exception:
        raise HTTPException(422,"Could not parse file")
    if df.empty or len(df)>200000:
        raise HTTPException(422,"File is empty or exceeds 200,000 rows")
    df.columns=[str(c).strip() or "column_"+str(i) for i,c in enumerate(df.columns)]
    # Normalize duplicate names for safe per-column indexing.
    unique=[]
    used={}
    for c in df.columns:
        used[c]=used.get(c,0)+1
        unique.append(c if used[c]==1 else c+"_"+str(used[c]))
    df.columns=unique
    df=df.replace([np.inf,-np.inf],np.nan)
    total=df.size
    completeness=round(100*df.notna().sum().sum()/total,2) if total else 0
    duplicates=int(df.duplicated().sum())
    cols=[]
    for c in df.columns:
        s=df[c]
        cols.append({"name":c,"dtype":str(s.dtype),"missing":int(s.isna().sum()),"missing_pct":round(100*s.isna().mean(),2),"unique":int(s.nunique(dropna=True))})
    numeric=[c for c in df.select_dtypes(include="number").columns if df[c].notna().sum()>=3]
    summary=[]
    for c in numeric[:20]:
        s=df[c].dropna()
        summary.append({"name":c,"mean":num(s.mean()),"median":num(s.median()),"std":num(s.std()),"min":num(s.min()),"max":num(s.max())})
    corr=[]
    for i,a in enumerate(numeric[:12]):
        for b in numeric[i+1:12]:
            paired=df[[a,b]].dropna()
            if len(paired)<5 or paired[a].nunique()<2 or paired[b].nunique()<2:
                continue
            r,p=stats.pearsonr(paired[a].astype(float),paired[b].astype(float))
            if math.isfinite(r):
                corr.append({"a":a,"b":b,"r":num(r),"p_value":num(p),"sample_size":len(paired)})
    corr.sort(key=lambda x:abs(x["r"]),reverse=True)
    insights=[{"title":"Dataset completeness","evidence":str(completeness)+"% of cells contain values.","recommendation":"Review missingness by variable before cleaning.","method":"Completeness audit"}]
    if duplicates:
        insights.append({"title":"Exact duplicate rows","evidence":str(duplicates)+" rows are identical to another row.","recommendation":"Check whether repeat records are legitimate events.","method":"Duplicate detection"})
    if corr:
        c=corr[0]
        insights.append({"title":"Strongest numerical association","evidence":c["a"]+" and "+c["b"]+" have r="+str(c["r"])+" (n="+str(c["sample_size"])+").","recommendation":"Investigate confounders. Correlation does not establish causation.","method":"Pearson correlation"})
    if len(df)<30:
        insights.append({"title":"Small sample","evidence":"Dataset contains only "+str(len(df))+" observations.","recommendation":"Interpret estimates cautiously and collect more representative data.","method":"Sample size check"})
    quality=round(max(0,0.85*completeness+15*(1-duplicates/len(df))),2)
    return {"filename":file.filename,"rows":len(df),"columns_count":len(df.columns),"quality_score":quality,"completeness":completeness,"duplicates":duplicates,"columns":cols,"numeric_summary":summary,"correlations":corr,"insights":insights,"limitations":["Associations are exploratory and do not establish causal effects.","P-values are unadjusted for multiple testing.","Data quality score is a heuristic, not an external certification.","Numeric profiling does not replace domain-specific modeling."]}

class ExplainRequest(BaseModel):
    analysis: dict
    question: str="Summarize these findings"

@app.post("/explain")
async def explain(body: ExplainRequest, user: str=Depends(auth)):
    secret=os.getenv("ANTHROPIC_API_KEY")
    if not secret:
        raise HTTPException(503,"Claude API key is not configured")
    approved={k:body.analysis.get(k) for k in ("rows","columns_count","completeness","duplicates","quality_score","numeric_summary","correlations","insights","limitations")}
    data=json.dumps(approved,default=str)[:12000]
    try:
        async with httpx.AsyncClient(timeout=55) as client:
            response=await client.post("https://api.anthropic.com/v1/messages",headers={"x-api-key":secret,"anthropic-version":"2023-06-01","content-type":"application/json"},json={"model":os.getenv("ANTHROPIC_MODEL","claude-sonnet-4-5"),"max_tokens":850,"system":"Use only verified facts in the JSON. Never fabricate figures, infer causality from correlations, or invent test results. Note uncertainty. Suggest practical next steps.","messages":[{"role":"user","content":body.question+"\nComputed findings: "+data}]})
        if response.status_code>=400:
            raise HTTPException(502,"Claude provider unavailable, HTTP "+str(response.status_code))
        answer="\n".join(x.get("text","") for x in response.json().get("content",[]) if x.get("type")=="text")
        return {"answer":answer}
    except httpx.RequestError:
        raise HTTPException(502,"Claude provider connection failed")
