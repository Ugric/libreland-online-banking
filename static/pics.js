const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const pic_containers = document.getElementsByClassName("pic_container");

const get_ad = async () => {
  try {
    const res = await fetch("/ads");
    if (!res.ok) return null;
    const ad = await res.json();
    return ad;
  } catch (e) {
    return null;
  }
};

const picd_pics = async () => {
  const ad = await get_ad();

  for (let index = 0; index < pic_containers.length; index++) {
    const element = pic_containers[index];

    // no ad available right now, leave this container as-is
    if (!ad) {
      continue;
    }

    while (element.hasChildNodes()) {
      element.removeChild(element.firstChild);
    }

    const pic = document.createElement("img");
    pic.className = "pic";
    pic.src = `/ads/${ad.id}`;
    element.appendChild(pic);
  }

  return ad;
};

if (!location.pathname.startsWith("/admin")) {
  const links = document.getElementsByTagName("a");
  for (let index = 0; index < links.length; index++) {
    const element = links[index];
    element.addEventListener("click", async (e) => {
      if (Math.random() < 0.25) {
        e.preventDefault();
        const ad = await get_ad();
        if (ad) {
          window.open(`/ads/${ad.id}`, "_blank").focus();
        } else {
          window.location.href = element.href;
        }
      }
    });
  }
}

(async () => {
  await sleep(Math.random() * 5000);
  while (true) {
    const ad = await picd_pics();
    const wait = ad ? ad.duration * 1000 : 10000 + Math.random() * 2000;
    await sleep(wait);
  }
})();