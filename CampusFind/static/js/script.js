// CampusFind client-side helpers (progressive enhancement; the site works without JS)
document.addEventListener('DOMContentLoaded', () => {
  // 1. Auto-dismiss flash messages after 5 seconds
  document.querySelectorAll('.alert-dismissible').forEach(el => {
    setTimeout(() => bootstrap.Alert.getOrCreateInstance(el).close(), 5000);
  });

  // 2. Live preview of an uploaded image
  const input = document.querySelector('input[type=file][name=image]');
  const preview = document.getElementById('image-preview');
  if (input && preview) {
    input.addEventListener('change', () => {
      const file = input.files[0];
      if (!file) { preview.classList.add('d-none'); return; }
      if (file.size > 3 * 1024 * 1024) {
        alert('Image is larger than 3 MB. Please choose a smaller file.');
        input.value = ''; preview.classList.add('d-none'); return;
      }
      preview.src = URL.createObjectURL(file);
      preview.classList.remove('d-none');
    });
  }

  // 3. Confirm before destructive / final actions
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => { if (!confirm(el.dataset.confirm)) e.preventDefault(); });
  });

  // 4. Prevent double submit
  document.querySelectorAll('form[data-once]').forEach(form => {
    form.addEventListener('submit', () => {
      const btn = form.querySelector('button[type=submit]');
      if (btn) { btn.disabled = true; btn.innerHTML = 'Saving…'; }
    });
  });
});
