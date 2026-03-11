# Installation

```shell
poetry install --all-extras
```

# Default database settings

```
host: localhost
port: 5432
user: postgres
password: postgres
database: task2_db
```

# Running linters

```shell
poetry run black . --check
poetry run isort . --check
poetry run mypy .
```


# Running tests

```shell
poetry run pytest
```

# Initializing empty db

```shell
poetry run python manage.py migrate
```

# Inserting empty company to the db

```shell
poetry run python manage.py seed
```

# Running the server

```shell
poetry run python manage.py runserver
```

# Sending request to app

```shell
curl --request PATCH 'http://127.0.0.1:8000/api/v1.0/company/2374910283749102' \
--header 'Content-Type: application/json' \
--data '{
    "pid": "2374910283749102",
    "name": "Acme Inc.",
    "date_of_incorporation": "2020-01-15",
    "taxinfo": [
        {
            "pid": "9843271092834710",
            "tin": "COMPANYTIN123",
            "country": "US"
        }
    ],
    "directors": [
        {
            "pid": "5839201748293746",
            "full_name": "Jane Smith",
            "taxinfo": [
                {
                    "pid": "1029384756102938",
                    "tin": "123456789",
                    "country": "US"
                }
            ],
            "identity_files": [
                {
                    "pid": "2345678912345678"
                },
                {
                    "pid": "3456789123456789"
                }
            ]
        }
    ],
    "shareholders": [
        {
            "pid": "9988776655443322",
            "full_name": "Alex Johnson",
            "percentage": 25,
            "identity_files": [
                {
                    "pid": "1122334455667788"
                },
                {
                    "pid": "2233445566778899"
                }
            ]
        }
    ]
}'
```
