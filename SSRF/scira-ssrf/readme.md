```
# install node npm pnpm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 22
node -v && npm -v

node -v              # ≥ 22
corepack enable
corepack prepare pnpm@latest --activate
pnpm -v


# git clone scira
git clone https://github.com/zaidmukaddam/scira.git

cd scira
ls app/api/proxy-image/          
cat package.json | head -40      
cat .env.example     

# PostgreSQL
docker run -d --name scira-pg \
  -e POSTGRES_USER=scira -e POSTGRES_PASSWORD=scira -e POSTGRES_DB=scira \
  -p 5432:5432 postgres:16

# Redis
docker run -d --name scira-redis -p 6379:6379 redis:7
```

