document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.navbar-toggle');
  const nav = document.getElementById('nav-links');
  if (!toggle || !nav) {
    console.error('Элементы навбара не найдены');
    return;
  }
  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') === 'true' || false;
    toggle.setAttribute('aria-expanded', !expanded);
    nav.classList.toggle('open');
  });
});



setTimeout(() => {
  const alerts = document.querySelectorAll('.alert.show');
  alerts.forEach(alert => {
    alert.classList.remove('show');
    alert.classList.add('fade');
    setTimeout(() => alert.remove(), 500);
  });
}, 3000);





