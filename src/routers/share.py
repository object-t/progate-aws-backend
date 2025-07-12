from fastapi import APIRouter, HTTPException, Depends, Query
import models.structure as structure_models
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
import json
from datetime import datetime
from settings import get_DynamoDbConnect
from routers.extractor import extract_user_id_from_token
from math import ceil

share_router = APIRouter()

dynamosettings = get_DynamoDbConnect()

DYNAMODB_ENDPOINT = dynamosettings.DYNAMODB_ENDPOINT
REGION = dynamosettings.REGION
AWS_ACCESS_KEY_ID = dynamosettings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = dynamosettings.AWS_SECRET_ACCESS_KEY

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=DYNAMODB_ENDPOINT,
    region_name=REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

table_name = "game"
table = dynamodb.Table(table_name)

@share_router.get("/share/structures", response_model=structure_models.SharedStructuresResponse)
async def get_shared_structures(page: int = Query(1, ge=1)):
    page_size = 10
    
    response = table.query(
        KeyConditionExpression=Key("PK").eq("shared") & Key("SK").begins_with("structure#"),
        FilterExpression=Attr("is_public").eq(True),
        ScanIndexForward=False
    )
    
    items = response.get("Items", [])
    total_count = len(items)
    
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    page_items = items[start_index:end_index]
    
    structures = []
    for item in page_items:
        structure = structure_models.SharedStructureSummary(
            structure_id=item["SK"].replace("structure#", ""),
            title=item.get("title", ""),
            description=item.get("description"),
            author_name=item.get("author_name"),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", "")
        )
        structures.append(structure)
    
    has_next = end_index < total_count
    
    return structure_models.SharedStructuresResponse(
        structures=structures,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_next=has_next
    )

@share_router.get("/share/structure/{structure_id}", response_model=structure_models.SharedStructure)
async def get_shared_structure(structure_id: str):
    response = table.get_item(
        Key={
            "PK": "shared",
            "SK": f"structure#{structure_id}"
        }
    )
    
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Structure not found")
    
    if not item.get("is_public", True):
        raise HTTPException(status_code=403, detail="Structure is not public")
    
    return structure_models.SharedStructure(
        structure_id=structure_id,
        title=item.get("title", ""),
        data=item.get("data", {}),
        description=item.get("description"),
        author_id=item.get("author_id", ""),
        author_name=item.get("author_name"),
        is_public=item.get("is_public", True),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", "")
    )

@share_router.put("/share/structure/{structure_id}")
async def update_shared_structure(
    structure_id: str, 
    request: structure_models.UpdateSharedStructureRequest,
    user_id: str = Depends(extract_user_id_from_token)
):
    response = table.get_item(
        Key={
            "PK": "shared",
            "SK": f"structure#{structure_id}"
        }
    )
    
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Structure not found")
    
    if item.get("author_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this structure")
    
    table.update_item(
        Key={
            "PK": "shared",
            "SK": f"structure#{structure_id}"
        },
        UpdateExpression="SET #data = :data, updated_at = :updated_at",
        ExpressionAttributeNames={"#data": "data"},
        ExpressionAttributeValues={
            ":data": request.data,
            ":updated_at": datetime.now().isoformat()
        }
    )
    
    return {"message": "Structure updated successfully"}

