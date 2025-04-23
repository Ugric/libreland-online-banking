const ads = ["/ads/tryones_chicken.png", "/ads/totum.png", "/ads/bank.png", "/ads/court.png", "/ads/log shop.png"];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const ad_containers = document.getElementsByClassName("ad_container");

const add_ads = () => {
  for (let index = 0; index < ad_containers.length; index++) {
    const element = ad_containers[index];
    while (element.hasChildNodes()) {
      element.removeChild(element.firstChild);
    }
    for (let index = 0; index < Math.floor(Math.random() * 0 + 1); index++) {
      const ad = document.createElement("img");
      ad.className = "ad";
      ad.src = ads[Math.floor(Math.random() * ads.length)];
      element.appendChild(ad);
    }
  }
};

(async () => {
  await sleep(Math.random() * 5000);
  while (true) {
    add_ads();
    await sleep(10000 + Math.random() * 2000);
  }
})();
