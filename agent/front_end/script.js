const searchBtn = document.getElementById("search-btn");
const cityInput = document.getElementById("city-input");
const chatBox = document.getElementById("chat-box");

const cityNameSpan = document.getElementById("city-name");
const tempSpan = document.getElementById("temp");
const humiditySpan = document.getElementById("humidity");
const windSpan = document.getElementById("wind");
const conditionSpan = document.getElementById("condition");
const suggestionP = document.getElementById("suggestion");

// 背景图映射表
const weatherBackgrounds = {
  "晴": "url('./asset/sunny.jpg')",
  "多云": "url('./asset/cloudy.jpg')",
  "阴": "url('./asset/cloudy1.jpg')",
  "雨": "url('./asset/rainy.jpg')",
  "雪": "url('./asset/snowy.jpg')"
};

// 点击“查看天气”按钮
searchBtn.addEventListener("click", () => {
  const city = cityInput.value.trim();
  
  // 定义三组示例数据（去掉了date字段）
  const weatherDataList = [
    {
      city: "福州市",
      temperature: 26,
      humidity: 68,
      wind: 3,
      condition: "多云转晴",
      suggestion: "天气舒适，适合出行，但早晚略凉，建议带薄外套。"
    },
    {
      city: "厦门市",
      temperature: 32,
      humidity: 68,
      wind: 3,
      condition: "晴",
      suggestion: "天气炎热，出行注意防晒。"
    },
    {
      city: "北京市",
      temperature: 22,
      humidity: 67,
      wind: 3,
      condition: "雨",
      suggestion: "气温适中，建议轻便外出，注意早晚温差。"
    }
  ];

  // 查找匹配项（只根据城市名匹配）
  const weatherData = weatherDataList.find(item => item.city === city);
  
  if (!weatherData) {
    addChat("系统", "暂无该城市的天气数据。");
    return;
  }

  // 更新天气信息
  cityNameSpan.textContent = weatherData.city;
  tempSpan.textContent = weatherData.temperature;
  humiditySpan.textContent = weatherData.humidity;
  windSpan.textContent = weatherData.wind;
  conditionSpan.textContent = weatherData.condition;
  suggestionP.textContent = weatherData.suggestion;


  // 聊天记录
  addChat("用户", `查询 ${city}`);
  addChat("系统", `${weatherData.city}天气：${weatherData.condition}，温度 ${weatherData.temperature}°C。${weatherData.suggestion}`);

  // 修改背景
  changeBackground(weatherData.condition);
});

// 聊天记录函数
function addChat(sender, message) {
  const p = document.createElement("p");
  p.innerHTML = `<strong>${sender}：</strong> ${message}`;
  chatBox.appendChild(p);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// 背景切换函数
function changeBackground(condition) {
  let normalized = condition.replace(/天|转/g, "").trim(); // 去除多余字符并修剪空格
  let matchedKey;

  switch (normalized) {
      case "晴": matchedKey = "晴"; break;
      case "多云": matchedKey = "多云"; break;
      case "阴": matchedKey = "阴"; break;
      case "雨": matchedKey = "雨"; break;
      case "雪": matchedKey = "雪"; break;
  }

  const bgUrl = weatherBackgrounds[matchedKey];
  if (bgUrl) {
      document.body.style.backgroundImage = bgUrl;
  } else {
      console.warn(`未找到对应背景图: ${matchedKey}`); // 调试用
      document.body.style.backgroundImage = weatherBackgrounds["多云"]; // 确保总有图可显示
  }
}