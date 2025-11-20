document.addEventListener('DOMContentLoaded', function() {
    const searchIcon = document.querySelector('.search-icon');
    const searchBox = document.querySelector('.search-box');
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    const searchContainer = document.querySelector('.search-container');

    // Toggle search box visibility
    searchIcon.addEventListener('click', function() {
        searchBox.style.display = searchBox.style.display === 'none' ? 'block' : 'none';
        if (searchBox.style.display === 'block') {
            searchInput.focus();
        }
    });

    // Handle search input
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        if (query.length > 0) {
            fetch(`/search_items?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    searchResults.innerHTML = '';
                    if (data.length > 0) {
                        data.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'search-result-item';

                            // Create a container for the image and text
                            const container = document.createElement('div');
                            container.style.display = 'flex';
                            container.style.alignItems = 'center';

                            // Add the image if it exists
                            if (item.Item_image) {
                                const img = document.createElement('img');
                                img.src = `data:image/jpeg;base64,${item.Item_image}`; // Assuming the image is JPEG
                                img.alt = item.Item_name;
                                img.style.width = '30px'; // Adjust size as needed
                                img.style.height = '30px';
                                img.style.marginLeft = '10px';
                                container.appendChild(img);
                            }

                            // Add the item name and weight
                            const text = document.createElement('span');
                            div.textContent = `${item.Item_name} (${item.Pur_unit_weight}g)`;
                            container.appendChild(text);

                            div.appendChild(container);

                            // Add click event to navigate to item details
                            div.dataset.itemId = item.Item_id;
                            div.dataset.unitWeight = item.Pur_unit_weight;
                            div.addEventListener('click', function() {
                                window.location.href = `/homeitem/${item.Item_id}?unit_weight=${item.Pur_unit_weight}`;
                            });
                            searchResults.appendChild(div);
                        });
                    } else {
                        searchResults.innerHTML = '<div class="search-result-item">No results found</div>';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    searchResults.innerHTML = '<div class="search-result-item">Error searching</div>';
                });
        } else {
            searchResults.innerHTML = '';
        }
    });

    // Close search box when clicking outside
    document.addEventListener('click', function(event) {
        if (!searchContainer.contains(event.target) && event.target !== searchIcon) {
            searchBox.style.display = 'none';
        }
    });
});