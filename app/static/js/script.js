document.addEventListener("DOMContentLoaded", function () {
  document
    .getElementById("sidebarCollapse")
    .addEventListener("click", function () {
      document.getElementById("sidebar").classList.toggle("active");
    });

  // Toggle sub-menu
  const dropdownToggles = document.querySelectorAll(".dropdown-toggle");
  dropdownToggles.forEach((toggle) => {
    toggle.addEventListener("click", function () {
      const target = document.querySelector(this.getAttribute("href"));
      target.classList.toggle("collapse");
      this.setAttribute(
        "aria-expanded",
        target.classList.contains("collapse") ? "false" : "true"
      );
    });
  });
});

// Add hidden input fields for selected document IDs
function addSelectedDocumentIdsToForm() {
  var form = document.getElementById("deleteDocumentsForm");
  form.innerHTML = ""; // Clear existing hidden inputs
  var checkboxes = document.querySelectorAll(
    'input[name="document_ids"]:checked'
  );
  checkboxes.forEach(function (checkbox) {
    var input = document.createElement("input");
    input.type = "hidden";
    input.name = "document_ids";
    input.value = checkbox.value;
    form.appendChild(input);
  });
}

// Toggle the visibility and functionality of the delete button
function toggleDeleteButton() {
  var checkboxes = document.querySelectorAll('input[name="document_ids"]');
  var deleteButton = document.getElementById("deleteSelectedButton");

  var anyChecked = Array.from(checkboxes).some((checkbox) => checkbox.checked);

  deleteButton.style.display = anyChecked ? "block" : "none";

  if (anyChecked) {
    deleteButton.onclick = function () {
      if (confirm("Are you sure you want to delete the selected documents?")) {
        addSelectedDocumentIdsToForm();
        document.getElementById("deleteDocumentsForm").submit();
      }
    };
  } else {
    deleteButton.onclick = null;
  }
}

// Toggle select all checkboxes
function toggleSelectAll() {
  const checkboxes = document.querySelectorAll('input[name="document_ids"]');
  const allChecked = Array.from(checkboxes).every(
    (checkbox) => checkbox.checked
  );
  checkboxes.forEach((checkbox) => (checkbox.checked = !allChecked));
  toggleDeleteButton();
}

// Initialize toggleDeleteButton on page load
document.addEventListener("DOMContentLoaded", function () {
  toggleDeleteButton(); // Ensure button state is correct on load
});
