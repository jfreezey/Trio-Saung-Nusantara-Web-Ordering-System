from pydantic import BaseModel, Field

class MenuCreate(BaseModel): #adding new menu
    name: str = Field(min_length=1)
    description: str = ""
    price: int = Field(gt=0)
    category_id: int
    is_available: bool = True

class MenuUpdate(BaseModel): #update current menu
    name: str = Field(min_length=1)
    description: str = ""
    price: int = Field(gt=0)
    category_id: int
    is_available: bool = True

class MenuAvailabilityUpdate(BaseModel): #availability menu(ada/gak ada)
    is_available: bool
