#!/bin/bash

function splash() {
  echo "本脚本会在 ${HOME}/YYeTs 部署人人影视web"
  echo "你确定要继续吗？输入YES确认"
  read -r confirm

  if [ "$confirm" = "YES" ]; then
    echo "继续安装"
  else
    echo "取消安装"
    exit 1
  fi

}

function prepare() {
  echo "[1/5] 准备中……"
  mkdir -p "${HOME}"/YYeTs
  cd "${HOME}"/YYeTs || exit
}

function prepare_compose() {
  echo "[2/5] 下载docker-compose.yml"
  curl -o docker-compose.yml https://raw.githubusercontent.com/tgbot-collection/YYeTsBot/master/docker-compose.yml
  sed -ie '31,67d' docker-compose.yml
}

function import_db() {
  echo "[3/5] 正在准备MongoDB"
  docker-compose up -d mongo

  echo "[4/5] 正在下载并导入数据库"
  curl -o /tmp/yyets_mongo.gz https://yyets.dmesg.app/dump/yyets_mongo.gz
  file /tmp/yyets_mongo.gz
  docker cp /tmp/yyets_mongo.gz yyets_mongo_1:/tmp
  # special for windows
  result=$(uname -a | grep "Msys")
  if [[ "$result" != "" ]]; then
    echo "docker exec yyets_mongo_1 mongorestore --gzip --archive=/tmp/yyets_mongo.gz --nsFrom "share.*" --nsTo "zimuzu.*"" >windows.bat
    echo "docker exec yyets_mongo_1 rm /tmp/yyets_mongo.gz" >>windows.bat
    cmd "/C windows.bat"
    rm windows.bat
  else
    docker exec yyets_mongo_1 mongorestore --gzip --archive=/tmp/yyets_mongo.gz --nsFrom "share.*" --nsTo "zimuzu.*"
    docker exec yyets_mongo_1 rm /tmp/yyets_mongo.gz
  fi

  rm /tmp/yyets_mongo.gz
}

function up() {
  echo "[5/5] 启动中……"
  docker-compose up -d
  echo "部署成功。您可以访问 http://IP:8888 查看"
}

function deploy() {
  splash
  prepare
  prepare_compose
  import_db
  up
}

function cleanup() {
  echo "您确认要进行清理吗？网站将会停止运行，对应的的docker image也将会被清除。输入YES确认"
  read -r confirm

  if [ "$confirm" = "YES" ]; then
    echo "继续清理，可能会要求您进行sudo鉴权"
    docker-compose -f "${HOME}"/YYeTs/docker-compose.yml down
    sudo rm -rf "${HOME}"/YYeTs
    docker rmi bennythink/yyetsbot
    echo "清理完成。"
  else
    echo "取消清理"
    exit 1
  fi

}

function upgrade() {
  docker pull bennythink/yyetsbot
  docker-compose -f "${HOME}"/YYeTs/docker-compose.yml up -d
  echo "更新成功"
}

select MENU_ITEM in "部署YYeTs" "清理YYeTs" "更新YYeTs"; do
  echo "准备$MENU_ITEM YYeTsWeb..."
  case $MENU_ITEM in
  "部署YYeTs") deploy ;;
  "清理YYeTs") cleanup ;;
  "更新YYeTs") upgrade ;;
  *) echo "无效的操作" ;;
  esac
  break
done
