from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(..., max_length=50, description="Username of the user")
    password: str = Field(..., max_length=255, description="Password of the user")
    email: str = Field(..., max_length=100, description="Email of the user")
    
    
class Artist(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=100, description="Name of the artist")
    country: str = Field(..., max_length=100, description="Country of the artist")
    bio: str | None = Field(default=None, description="Biography of the artist")

    tracks: list["Track"] = Relationship(back_populates="artist")

class Track(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(..., max_length=100, description="Title of the track")
    artist_id: int = Field(..., foreign_key="artist.id", description="ID of the artist")
    year: int = Field(..., ge=1900, description="Year of release")
    duration: int = Field(..., ge=0, description="Duration of the track in seconds")
    genres: str = Field(description="Genres of the track")
    file: str | None = Field(default=None, description="File path of the track")

    artist: Optional["Artist"] = Relationship(back_populates="tracks") 


class ArtistRead(SQLModel):
    id: int
    name: str
    country: str


class TrackRead(SQLModel):
    id: int
    title: str
    artist: Optional[ArtistRead] = None
    year: int
    duration: int
    genres: str
    file: Optional[str] = None


class TrackCreate(SQLModel):
    title: str = Field(..., max_length=100, description="Title of the track")
    artist_id: int = Field(..., description="ID of the artist")
    year: int = Field(..., ge=1900, description="Year of release")
    duration: int = Field(..., ge=0, description="Duration of the track in seconds")
    genres: str = Field(..., description="Genres of the track") 
    file: str | None = Field(default=None, description="File path of the track")

    
class ArtistCreate(SQLModel):
    name: str = Field(..., max_length=100, description="Name of the artist")
    country: str = Field(..., max_length=100, description="Country of the artist")
    bio: str | None = Field(default=None, description="Biography of the artist")

