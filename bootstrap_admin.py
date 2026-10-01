import argparse
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from core.security import get_password_hash
from database.session import SessionLocal
from models.usuario import PerfilEnum, Usuario


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria ou prepara uma conta ADMIN local.")
    parser.add_argument(
        "--reset-existing",
        action="store_true",
        help="Permite redefinir a senha do ADMIN existente com o login informado.",
    )
    args = parser.parse_args()

    login = input("Login do ADMIN [admin]: ").strip() or "admin"
    if len(login) > 50:
        print("O login deve ter no máximo 50 caracteres.")
        return 1

    senha = getpass("Nova senha (mínimo 6 caracteres): ")
    confirmacao = getpass("Confirme a senha: ")
    if senha != confirmacao:
        print("As senhas não conferem.")
        return 1
    if len(senha) < 6 or len(senha.encode("utf-8")) > 1024:
        print("A senha deve conter entre 6 e 1024 bytes UTF-8.")
        return 1

    try:
        with SessionLocal.begin() as db:
            usuario = db.scalar(select(Usuario).where(Usuario.login == login))
            if usuario is not None:
                if usuario.perfil != PerfilEnum.admin:
                    print("Esse login já pertence a um usuário que não é ADMIN.")
                    return 1
                if not args.reset_existing:
                    print(
                        "A conta ADMIN já existe. Use --reset-existing para "
                        "autorizar a redefinição."
                    )
                    return 1
                if not usuario.ativo:
                    print("A conta ADMIN existente está inativa; reative-a antes.")
                    return 1
                usuario.senha_hash = get_password_hash(senha)
                print(f"Senha atualizada para a conta ADMIN '{login}'.")
                return 0

            admin_ativo_id = db.scalar(
                select(Usuario.id)
                .where(
                    Usuario.perfil == PerfilEnum.admin,
                    Usuario.ativo.is_(True),
                )
                .limit(1)
            )
            if admin_ativo_id is not None:
                print(
                    "Já existe um ADMIN ativo. Entre com essa conta e crie outro "
                    "usuário pela API."
                )
                return 1

            db.add(
                Usuario(
                    nome="Administrador",
                    login=login,
                    senha_hash=get_password_hash(senha),
                    perfil=PerfilEnum.admin,
                    ativo=True,
                )
            )
        print(f"Conta ADMIN '{login}' criada.")
        return 0
    except SQLAlchemyError:
        print("Não foi possível preparar a conta ADMIN; confira o banco e DATABASE_URL.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())