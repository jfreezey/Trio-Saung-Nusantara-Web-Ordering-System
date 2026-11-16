from pydantic import BaseModel, Field

class CategoryCreate(BaseModel): #adding new category
    name: str = Field(min_length=1)
    description: str = ""
    
class CategoryUpdate(BaseModel): #update current category
    name: str = Field(min_length=1)
    description: str = ""
    