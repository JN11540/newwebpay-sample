// app/static/js/script.js
async function createOrder(softwareproductname, price) {
    try {
        const response = await fetch('/createOrder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                softwareproductname: softwareproductname,
                price: price
            })
        });

        if (response.redirected) {
            window.location.href = response.url; // Handle redirect if needed
        } else {
            const data = await response.json();
            if (response.ok) {
                alert('Order created successfully!');
            } else {
                alert('Failed to create order: ' + data.detail);
            }
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while creating the order.');
    }
}