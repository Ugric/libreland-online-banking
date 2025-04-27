const pics = [
  "/pics/tryones_chicken.png",
  "/pics/totum.png",
  "/pics/bank.png",
  "/pics/court.png",
  "/pics/log shop.png",
  "/pics/guardian.png",
  "/pics/freedom.png",
  "/pics/black_dog.png",
  "/pics/advert.png"
];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const pic_containers = document.getElementsByClassName("pic_container");

const picd_pics = () => {
  for (let index = 0; index < pic_containers.length; index++) {
    const element = pic_containers[index];
    while (element.hasChildNodes()) {
      element.removeChild(element.firstChild);
    }
    for (let index = 0; index < Math.floor(Math.random() * 0 + 1); index++) {
      const pic = document.createElement("img");
      pic.className = "pic";
      pic.src = pics[Math.floor(Math.random() * pics.length)];
      element.appendChild(pic);
    }
  }
};

if (!location.pathname.startsWith("/admin")) {
  const links = document.getElementsByTagName("a");
  for (let index = 0; index < links.length; index++) {
    const element = links[index];
    element.addEventListener("click", (e) => {
      if (Math.random() < 0.25) {
        e.preventDefault();
        window
          .open(pics[Math.floor(Math.random() * pics.length)], "_blank")
          .focus();
      }
    });
  }
}

(async () => {
  await sleep(Math.random() * 5000);
  while (true) {
    picd_pics();
    await sleep(10000 + Math.random() * 2000);
  }
})();
