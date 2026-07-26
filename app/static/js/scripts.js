/*!
    * Start Bootstrap - SB Admin v7.0.7 (https://startbootstrap.com/template/sb-admin)
    * Copyright 2013-2023 Start Bootstrap
    * Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-sb-admin/blob/master/LICENSE)
    */
    // 
// Scripts
// 

window.addEventListener('DOMContentLoaded', event => {

    // Toggle the side navigation
    const sidebarToggle = document.body.querySelector('#sidebarToggle');
    if (sidebarToggle) {
        // Uncomment Below to persist sidebar toggle between refreshes
        // if (localStorage.getItem('sb|sidebar-toggle') === 'true') {
        //     document.body.classList.toggle('sb-sidenav-toggled');
        // }
        sidebarToggle.addEventListener('click', event => {
            event.preventDefault();
            document.body.classList.toggle('sb-sidenav-toggled');
            localStorage.setItem('sb|sidebar-toggle', document.body.classList.contains('sb-sidenav-toggled'));
        });
    }

    // Product forms: only show subcategories belonging to the selected category.
    document.querySelectorAll('[data-category-parent]').forEach(parentSelect => {
        const childSelect = parentSelect.closest('.row').querySelector('[data-category-child]');
        if (!childSelect) return;

        const updateSubcategories = () => {
            const selectedParent = parentSelect.value;
            let selectedOptionIsVisible = false;

            Array.from(childSelect.options).forEach(option => {
                if (!option.dataset.parentId) return;
                const isVisible = option.dataset.parentId === selectedParent;
                option.hidden = !isVisible;
                option.disabled = !isVisible;
                if (option.selected && isVisible) selectedOptionIsVisible = true;
            });

            childSelect.disabled = !selectedParent;
            if (!selectedOptionIsVisible) childSelect.value = '';
        };

        // On edit, infer the parent from the currently selected subcategory.
        const selectedChild = childSelect.options[childSelect.selectedIndex];
        if (selectedChild && selectedChild.dataset.parentId) {
            parentSelect.value = selectedChild.dataset.parentId;
        }

        parentSelect.addEventListener('change', updateSubcategories);
        updateSubcategories();
    });

    // Auto-generate SKU when subcategory is selected (Add Product form only)
    const skuField = document.getElementById('sku_field');
    const subcategorySelect = document.getElementById('subcategory');
    if (skuField && subcategorySelect) {
        subcategorySelect.addEventListener('change', function() {
            const subcatId = this.value;
            if (!subcatId) return;

            // Fetch generated SKU from backend
            fetch(`/api/generate-sku?subcategory_id=${subcatId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.sku) {
                        skuField.value = data.sku;
                    }
                })
                .catch(error => {
                    console.error('SKU generation failed:', error);
                    // Leave SKU field editable as fallback
                });
        });
    }

});
