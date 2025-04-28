document.addEventListener('DOMContentLoaded', function() {
    const carousel = document.getElementById('face-carousel');
    let imageList = [];
  
    fetch('/api/approved-faces')
      .then(res => res.json())
      .then(data => {
        imageList = data;
        renderCarousel();
      });
  
    function renderCarousel() {
      carousel.innerHTML = '';
      imageList.forEach((name, index) => {
        const card = document.createElement('div');
        card.className = 'face_card';
  
        const img = document.createElement('img');
        img.src = `/camera/faces/${name}`;
        img.alt = name;
  
        const delBtn = document.createElement('button');
        delBtn.textContent = 'X';
        delBtn.className = 'face_delete-btn';
        delBtn.onclick = () => {
          if (confirm(`Are you sure you want to remove ${name}?`)) {
            fetch('/api/remove-face', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ filename: name })
            })
            .then(res => res.json())
            .then(response => {
              imageList.splice(index, 1);
              renderCarousel();
            });
          }
        };
  
        card.appendChild(img);
        card.appendChild(delBtn);
        carousel.appendChild(card);
      });
    }
  });
  