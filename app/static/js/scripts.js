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

    // Product forms: show/hide subcategories based on selected parent category
    const parentCatSelect = document.getElementById('parent_category');
    const childCatSelect = document.getElementById('subcategory');

    if (parentCatSelect && childCatSelect) {
        const updateSubcategories = () => {
            const selectedParent = parentCatSelect.value;
            let foundVisible = false;

            // Loop through subcategory options and show/hide based on parent
            for (let i = 0; i < childCatSelect.options.length; i++) {
                const option = childCatSelect.options[i];
                if (!option.dataset.parentId) continue;
                const isVisible = option.dataset.parentId === selectedParent;
                option.hidden = !isVisible;
                option.disabled = !isVisible;
                if (option.selected && isVisible) foundVisible = true;
            }

            // Enable/disable subcategory dropdown based on parent selection
            childCatSelect.disabled = !selectedParent;
            if (!foundVisible) childCatSelect.value = '';
        };

        // On edit page: infer parent from currently selected subcategory
        const selectedChild = childCatSelect.options[childCatSelect.selectedIndex];
        if (selectedChild && selectedChild.dataset.parentId) {
            parentCatSelect.value = selectedChild.dataset.parentId;
        }

        parentCatSelect.addEventListener('change', updateSubcategories);
        updateSubcategories();
    }

    // Auto-generate SKU on Add Product form
    const skuField = document.getElementById('sku_field');
    
    if (skuField) {
        const fetchSku = (params) => {
            const qs = Object.entries(params).map(([k, v]) => `${k}=${v}`).join('&');
            fetch(`/api/generate-sku?${qs}`)
                .then(r => r.json())
                .then(data => {
                    if (data.success && data.sku) skuField.value = data.sku;
                })
                .catch(err => console.error('SKU generation failed:', err));
        };

        // When subcategory is selected (e.g., Keyboard -> Mechanical, Membrane)
        if (childCatSelect) {
            childCatSelect.addEventListener('change', function() {
                if (this.value) fetchSku({ subcategory_id: this.value });
            });
        }

        // When parent category is selected AND no subcategory options exist
        // (e.g., Mouse, Monitors have no subcategories)
        if (parentCatSelect) {
            parentCatSelect.addEventListener('change', function() {
                const catId = this.value;
                if (!catId) return;

                // Check if this category has any subcategories visible
                setTimeout(() => {
                    const hasVisible = Array.from(childCatSelect.options).some(
                        o => o.dataset.parentId === catId && !o.hidden
                    );
                    if (!hasVisible) {
                        fetchSku({ category_id: catId });
                    }
                }, 0);
            });
        }
    }


});
