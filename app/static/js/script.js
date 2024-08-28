// app/static/js/script.js
async function createOrder(softwareproductname, price) {
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

    const data = await response.json();
    if (response.ok) {
        alert('Order created successfully!');
    } else {
        alert('Failed to create order: ' + data.detail);
    }
}