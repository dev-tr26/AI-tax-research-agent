import _asyncio
import json 
import time 
from contextlib import asynccontextmanager
from typing import Optional, AsyncIterator
import uvicorn 
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Request

from config import get_settings
from db.database import init_db
from agents.pipeline import get_pipeline