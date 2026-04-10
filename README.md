# Seven-Plus-Academy
# Desctiprion
This is a BISP project for the BIS Bachelors at the WIUT. It is a Student/School management Web App where Admins and Teachers manage multiple School related components such as attendances, payments, groups. Students can view their own related data.


# Setup Instructions

# Prequisites:
Docker and docker compose should installed. 

# 1. Clone the repository
git clone https://github.com/IslombekMir/Seven-Plus-Academy
cd Seven-Plus-Academy

# 2. Create your environment file
cp .env.example .env

# 3. Build and start the containers
docker compose up --build -d

# 4. Run migrations and create a superuser
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser