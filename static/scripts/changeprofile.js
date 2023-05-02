function previewProfilePicture(event) {
    const preview = document.querySelector('#profile-picture-preview');
    preview.src = URL.createObjectURL(event.target.files[0]);
}