// Reveal-on-scroll
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (e.isIntersecting) {
      e.target.classList.add('in');
      io.unobserve(e.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });

document.querySelectorAll('.reveal').forEach((el) => io.observe(el));

// Live temperature ticker in the spec strip (subtle)
const tempEl = document.getElementById('liveTemp');
if (tempEl) {
  let t = 102;
  setInterval(() => {
    t = 101 + Math.random() * 2;
    tempEl.textContent = t.toFixed(1);
  }, 1800);
}

// Parallax on hero device
const heroImg = document.querySelector('.hero-image-wrap img');
if (heroImg && window.matchMedia('(min-width: 900px)').matches) {
  document.addEventListener('mousemove', (e) => {
    const x = (e.clientX / window.innerWidth - 0.5) * 14;
    const y = (e.clientY / window.innerHeight - 0.5) * 10;
    heroImg.style.transform = `translate(${x}px, ${y}px)`;
  });
}
