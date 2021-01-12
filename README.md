# LineBot看診號

[![截圖](https://github.com/img21326/LineBotWatchDoctor/blob/main/screenshot.png?raw=true)]()

### 功能說明

簡單地向LINE機器人發送要看診的科目，機器人就會自動幫你找資料，並回傳看診進度
(每五分鐘更新一次資料)，爬蟲程式碼以jupyter開發，有興趣可以參考 [此連結](https://github.com/img21326/LineBotWatchDoctor/blob/main/%E7%88%AC%E8%9F%B2.ipynb)，快取存入pickle之中，並在每次執行時檢查時間是否超過五分鐘(目前未處理併發問題)。

### LIB

  - flask
  - linebotsdk
  - requests
  - bs4

### Deploy

建議用Docker在部署上會比較方便，直接docker-compose起來就可以，編譯已經寫在裡面，可以參考Dockerfile的設置。

```sh
    export LINE_CHANNEL_SECRET=你的LINE_SECRET
    export LINE_CHANNEL_ACCESS_TOKEN=你的LINE_CHANNEL_ACCESS_TOKEN
    docker-compose up -d
```

#### Docker Console

[![截圖2](https://github.com/img21326/LineBotWatchDoctor/blob/main/screenshot2.png?raw=true)]()
