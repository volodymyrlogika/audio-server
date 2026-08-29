import shutil
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException,  Query, Form, File, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy.orm import selectinload
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pathlib import Path
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta


from models import Track, TrackRead, Artist, ArtistRead, User, ArtistCreate, TrackCreate

SECRET_KEY = "19109197bd5e327c289b92b2b355083ea26c71dee2085ceccc19308a7291b2ea06"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60*24

AUDIO_TYPES = ["audio/mpeg", 'audio/mp3', "audio/wav", "audio/flac", "audio/ogg", "audio/aac", "audio/webm"]
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)


def token_create(data: dict):
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or form_data.password != user.password:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = token_create(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/tracks/all", response_model=list[TrackRead])
def get_all_tracks(session: SessionDep, ):
    tracks = session.exec(select(Track).options(selectinload(Track.artist))).all()
    return tracks


@app.get("/tracks/{track_id}", response_model=TrackRead) 
def get_track(track_id: int, session: SessionDep):
    track = session.exec(select(Track).where(Track.id == track_id).options(selectinload(Track.artist))).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    return track

@app.post("/tracks/add", response_model=TrackRead, status_code=201)
def add_new_track(session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)],
                  title: str = Form(..., max_length=100, description="Title of the track"),
                   artist_id: int = Form(..., description="ID of the artist"),
                   year: int = Form(..., ge=1900, description="Year of release"),
                   duration: int = Form(..., ge=0, description="Duration of the track in seconds"),
                   genres: str = Form(..., description="Genres of the track"),
                   file: UploadFile | None = File(default=None, description="File of the track")
                  ):
    # 1. Валідація - перевірка чи існує артист з таким artist_id та перевірка типу файлу, якщо він наданий
    artist = session.get(Artist, artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    if file and file.filename:
        if file.content_type not in AUDIO_TYPES:
            raise HTTPException(status_code=400, detail="Invalid file type. Only audio files are allowed.")
        
    # 2. Збереження в базу даних (без файлу)
    track = Track(title=title, artist_id=artist_id, year=year, duration=duration, genres=genres)
    
    session.add(track)
    session.commit()
    session.refresh(track)
    # 3. Збереження файлу на диск, якщо він наданий
    if file and file.filename:
        extension = Path(file.filename).suffix
        file_path = UPLOADS_DIR / f"track_{track.id}{extension}"

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        track.file = str(file_path)
        session.add(track)
        session.commit()
        session.refresh(track)  

    return track



@app.post("/artists/add", response_model=ArtistRead, status_code=201)
def add_new_artist(artist: ArtistCreate, session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]):
    artist_db = Artist(name=artist.name, country=artist.country, year_of_birth=artist.year_of_birth)
    session.add(artist_db)
    session.commit()
    session.refresh(artist_db)

    return artist_db


@app.delete("/tracks/{track_id}")
def delete_track(track_id: int, session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]):
    track = session.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    session.delete(track)
    session.commit()
    return {"message": "Track deleted"}


@app.get('/tracks/{track_id}/audio')
def get_track_audio(track_id: int, session: SessionDep):
    track = session.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    if not track.file:
        raise HTTPException(status_code=404, detail="Audio file not found for this track")

    return FileResponse(path=track.file, media_type="audio/mpeg", filename=Path(track.file).name)