"""
Módulo de seguridad y autenticación de usuarios.
"""
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from passlib.handlers import bcrypt
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone


from app.settings import settings
from app.schemas import TokenData, Token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityService:
    """
    Servicio de seguridad y autenticación de usuarios.
    """
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verificar una contraseña plana contra una contraseña hash.

        Args:
            plain_password (str): La contraseña plana a verificar.
            hashed_password (str): El hash de la contraseña a comparar.

        Returns:
            bool: True si las contraseñas coinciden, False en caso contrario.
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Hash una contraseña plana utilizando bcrypt.

        Args:
            password (str): La contraseña plana a hashear.

        Returns:
            str: La contraseña hasheada.
        """
        return pwd_context.hash(password)

    @staticmethod
    def _create_generic_token(data: dict, expires_delta: timedelta, scope: str) -> str:
        """
        Helper interno para crear un token JWT con un alcance específico.

        Args:
            data (dict): Data a incluir en el payload (claims).
            expires_delta (timedelta): Tiempo hasta que expire el token.
            scope (str): El propósito del token (access, reset, email).

        Returns:
            str: La cadena JWT codificada.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire, "scope": scope})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> Token:
        """
        Crea un token JWT de acceso para sesiones de usuario.

        Args:
            data (dict): Diccionario que contiene 'sub' (ID del usuario).
            expires_delta (Optional[timedelta]): Tiempo de expiración personalizado.

        Returns:
            Token: El modelo Pydantic Token que contiene el JWT.
        """
        delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        encoded_jwt = SecurityService._create_generic_token(data, delta, scope="access")
        return Token(access_token=encoded_jwt, token_type="bearer")

    @staticmethod
    def create_password_reset_token(user_id: str) -> str:
        """
        Crea un token de recuperación de contraseña expirado en 25 minutos.

        Args:
            user_id (str): El ID del usuario solicitando la recuperación de contraseña.

        Returns:
            str: El token JWT codificado (25 minutos de expiración).
        """
        return SecurityService._create_generic_token(
            {"sub": user_id}, 
            timedelta(minutes=25), 
            scope="password_reset"
        )

    @staticmethod
    def create_email_verification_token(user_id: str) -> str:
        """
        Crea un token para la verificación de dirección de correo electrónico.

        Args:
            user_id (str): ID del usuario a verificar.

        Returns:
            str: El token JWT codificado (60 minutos de expiración).
        """
        return SecurityService._create_generic_token(
            {"sub": user_id}, 
            timedelta(minutes=60), 
            scope="email_verify"
        )

    @staticmethod
    def decode_token(token: str, expected_scope: str) -> TokenData:
        """
        Decodifica y valida un token JWT basado en el alcance esperado (scoop).

        Args:
            token (str): La cadena JWT a decodificar.
            expected_scope (str): El alcance o scoop esperado (access, password_reset, o email_verify).

        Returns:
            TokenData: Datos validos del token.

        Raises:
            HTTPException: Si el token es inválido, expira o tiene el alcance incorrecto.
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            token_scope: str = payload.get("scope")

            if user_id is None or token_scope != expected_scope:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid credentials or incorrect token scope: {expected_scope}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(user_id=user_id)
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials or token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )