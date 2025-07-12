

from fastapi import APIRouter, HTTPException, Depends, Query
import models.structure as structure_models
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
from datetime import datetime
from settings import get_DynamoDbConnect
from routers.extractor import extract_user_id_from_token

share_router = APIRouter()

dynamosettings = get_DynamoDbConnect()

REGION = dynamosettings.REGION

dynamodb = boto3.resource(
    "dynamodb",
    region_name=REGION,
)

table_name = "game"
table = dynamodb.Table(table_name)

@share_router.get("/share/structures", response_model=structure_models.SharedStructuresResponse)
async def get_shared_structures(page: int = Query(1, ge=1)):
    page_size = 10
    
    response = table.scan(
        FilterExpression=Attr("SK").begins_with("sandbox#") & Attr("is_published").eq(True)
    )
    
    items = response.get("Items", [])
    total_count = len(items)
    
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    page_items = items[start_index:end_index]
    
    structures = []
    for item in page_items:
        sandbox_id = item["SK"].replace("sandbox#", "")
        structure = structure_models.SharedStructureSummary(
            structure_id=sandbox_id,
            title=item.get("title", f"Structure {sandbox_id}"),
            description=item.get("description"),
            author_name=item.get("author_name"),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", item.get("created_at", ""))
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
    response = table.scan(
        FilterExpression=Attr("SK").eq(f"sandbox#{structure_id}")
    )
    
    items = response.get("Items", [])
    if not items:
        raise HTTPException(status_code=404, detail="Structure not found")
    
    item = items[0]
    if not item.get("is_published", False):
        raise HTTPException(status_code=403, detail="Structure is not published")
    
    user_id = item["PK"].replace("user#", "")
    
    return structure_models.SharedStructure(
        structure_id=structure_id,
        title=item.get("title", f"Structure {structure_id}"),
        data=item.get("struct", {}),
        description=item.get("description"),
        author_id=user_id,
        author_name=item.get("author_name"),
        is_public=item.get("is_published", False),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", item.get("created_at", ""))
    )

@share_router.put("/share/structure/{structure_id}")
async def update_shared_structure(
    structure_id: str, 
    request: structure_models.UpdateSharedStructureRequest,
    user_id: str = Depends(extract_user_id_from_token)
):
    pk = f"user#{user_id}"
    sk = f"sandbox#{structure_id}"
    
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

@share_router.post("/share/structure", response_model=structure_models.CreateSharedStructureResponse)
async def create_shared_structure(
    request: structure_models.CreateSharedStructureRequest,
    user_id: str = Depends(extract_user_id_from_token)
):
    sandbox_id = str(uuid.uuid4())
    pk = f"user#{user_id}"
    sk = f"sandbox#{sandbox_id}"
    
    sandbox_item = {
        "PK": pk,
        "SK": sk,
        "struct": request.data,
        "title": request.title,
        "description": request.description,
        "is_published": request.is_public,
        "author_id": user_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    table.put_item(Item=sandbox_item)
    
    return structure_models.CreateSharedStructureResponse(
        structure_id=sandbox_id,
        message="Structure created successfully"
    )

