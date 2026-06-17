from sqlalchemy import Column, Integer, String, DateTime, Enum, UniqueConstraint
from sqlalchemy.sql import func
from database import Base

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    file_md5 = Column(String(32), index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    status = Column(Enum('uploading', 'completed', 'failed'), default='uploading')
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('file_md5', 'chunk_index', name='uq_file_md5_chunk_index'),
    )
