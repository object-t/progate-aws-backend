

from fastapi import APIRouter, HTTPException, Depends, Query
import models.share as share_models
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
from datetime import datetime
from settings import get_DynamoDbSettings
from routers.extractor import extract_user_id_without_verification

share_router = APIRouter()

dynamosettings = get_DynamoDbSettings()

REGION = dynamosettings.REGION

dynamodb = boto3.resource(
    "dynamodb",
    region_name=REGION,
)

table_name = "game"
table = dynamodb.Table(table_name)

@share_router.get("/share/structures", response_model=share_models.SharedStructuresResponse)
async def get_shared_structures(page: int = Query(1, ge=1), user_id: str = Depends(extract_user_id_without_verification)):

    page_size = 10
    
    response = table.query(
        FilterExpression=Attr("SK").begins_with("sandbox#") & Attr("is_public").eq(True)
    )
    
    items = response.get("Items", [])
    total_count = len(items)
    
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    page_items = items[start_index:end_index]
    
    structures = []
    for item in page_items:
        sandbox_id = item["SK"].replace("sandbox#", "")
        structure = share_models.SharedStructureSummary(
            user_id, user_id,
            sandbox_id, sandbox_id,
            struct=item.get("struct"),
            is_public=item.get("is_public"),
            created_at=item.get("created_at", ""),
        )
        structures.append(structure)
    
    has_next = end_index < total_count
    
    return share_models.SharedStructuresResponse(
        structures=structures,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_next=has_next
    )

@share_router.get("/share/structure/{sandbox_id}", response_model=share_models.SharedStructure)
async def get_shared_structure(sandbox_id: str):
    response = table.query(
        FilterExpression=Attr("SK").eq(f"sandbox#{sandbox_id}")
    )
    
    items = response.get("Items", [])
    if not items:
        raise HTTPException(status_code=404, detail="Structure not found")
    
    item = items[0]
    if not item.get("is_public", False):
        raise HTTPException(status_code=403, detail="Structure is not public")
    
    user_id = item["PK"].replace("user#", "")
    
    return share_models.SharedStructure(
        user_id, user_id,
        sandbox_id, sandbox_id,
        struct=item.get("struct"),
        is_public=item.get("is_public", False),
        created_at=item.get("created_at", ""),
    )

@share_router.put("/share/structure/{sandbox_id}")
async def update_shared_structure(
    sandbox_id: str, 
    request: share_models.UpdateSharedStructureRequest,
    user_id: str = Depends(extract_user_id_without_verification)
):
    pk = f"user#{user_id}"
    sk = f"sandbox#{sandbox_id}"
    
    response = table.get_item(
        Key={
            "PK": pk,
            "SK": sk
        }
    )
    
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Structure not found")
    
    table.update_item(
        Key={
            "PK": pk,
            "SK": sk
        },
        UpdateExpression="SET #struct = :data, updated_at = :updated_at",
        ExpressionAttributeNames={"#struct": "struct"},
        ExpressionAttributeValues={
            ":data": request.data,
            ":updated_at": datetime.now().isoformat()
        }
    )
    
    return {"message": "Structure updated successfully"}