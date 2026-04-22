from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from cryptography.fernet import Fernet

from app.database.base import Base
from app.config import settings

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(LargeBinary)
    is_active = Column(Boolean, default=False)

    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role", back_populates="users")
    staff = relationship("Staff", back_populates="user")

    def _get_fernet(self):
        key = settings.ENCRYPTION_KEY
        return Fernet(key.encode())

    def decrypt_password(self):
        fernet = self._get_fernet()
        decrypted_password_bytes = fernet.decrypt(self.hashed_password)
        return decrypted_password_bytes.decode()

    def verify_password(self, password: str) -> bool:
        try:
            decrypted_stored_password = self.decrypt_password()
            return decrypted_stored_password == password
        except Exception:
            return False

    def set_password(self, password: str):
        fernet = self._get_fernet()
        encrypted_password_bytes = fernet.encrypt(password.encode())
        self.hashed_password = encrypted_password_bytes

    @property
    def role_name(self) -> str | None:
        return self.role.name if self.role else None
