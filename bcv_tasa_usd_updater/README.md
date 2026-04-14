# bcv_tasa_usd_updater

## Overview
The `bcv_tasa_usd_updater` project is designed to manage and update exchange rate data for the Venezuelan bolívar (VES) against the US dollar (USD). It includes a stored procedure for inserting and updating exchange rates, along with error logging capabilities.

## Project Structure
```
bcv_tasa_usd_updater
├── sql
│   ├── procs
│   │   └── alter_sp_carga_tasa_raise_and_log.sql
│   ├── migrations
│   │   ├── 0001_create_tasas_dicom.sql
│   │   └── 0002_create_log_sp_errors.sql
│   ├── views
│   │   └── -- keep view definitions here
│   └── functions
│       └── -- scalar/table-valued functions
├── scripts
│   ├── deploy.sql
│   └── rollback.sql
├── tests
│   └── integration
│       └── test_sp_carga_tasa.sql
├── docs
│   └── compatibility.md
├── .gitignore
├── LICENSE
└── README.md
```

## Setup Instructions
1. **Database Setup**: 
   - Execute the migration scripts located in the `sql/migrations` directory to create the necessary tables (`tasas_dicom` and `log_sp_errors`).
   
2. **Deploying the Schema**: 
   - Run the `scripts/deploy.sql` script to set up the initial database schema and any required data.

3. **Testing**: 
   - Use the integration tests in `tests/integration/test_sp_carga_tasa.sql` to validate the functionality of the stored procedure `sp_carga_tasa`.

## Usage
- The stored procedure `sp_carga_tasa` can be called to insert or update exchange rate data. It includes error handling that logs any issues encountered during execution.

## Contribution
Contributions to the project are welcome. Please ensure that any changes are well-documented and tested.

## License
This project is licensed under the terms specified in the LICENSE file.