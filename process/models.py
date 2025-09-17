
from datetime import datetime
from typing import List, Optional, Dict, Any
import re
from pydantic import BaseModel, field_validator, ConfigDict


class Virksomhed(BaseModel):

    cvr: str
    pNummer: str
    virksomhedsnavn: str
    
    virksomhedsreferenceId: str
    aktiv: bool
    kommunekode: int



    @field_validator('cvr')
    @classmethod
    def validate_cvr(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('CVR kan ikke være tomt')
        return v.strip()
    
    @field_validator('pNummer')
    @classmethod
    def validate_pnummer(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('P-nummer kan ikke være tomt')
        return v.strip()
    
    @field_validator('virksomhedsreferenceId')
    @classmethod
    def validate_virksomhedsreference_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Virksomhedsreference ID kan ikke være tomt')
        
        # GUID pattern: 8-4-4-4-12 hexadecimal digits
        guid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        
        if not guid_pattern.match(v.strip()):
            raise ValueError('Virksomhedsreference ID skal være et gyldigt GUID format')
        
        return v.strip()



