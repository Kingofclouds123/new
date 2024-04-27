from flask import Flask, request, jsonify, render_template, redirect, send_file, url_for
from flask_pymongo import PyMongo
from bson import ObjectId
from gridfs import GridFS
from io import BytesIO
from flask_cors import CORS
import razorpay
import requests
from flask import Flask, request, jsonify
from twilio.rest import Client
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

twilio_client = Client("AC2d1a83302aee4efb8f6daab370baa71c", "edc705dcf2b16af6314603d99fdcd4af")
smtp_server = 'smtppro.zoho.in'
smtp_port = 465
smtp_username = 'manager@kingofclouds.in'
smtp_password = 'eyJt6NBJBva3'

app.config["MONGO_URI"] = "mongodb+srv://kingofcloudsin:King_of_clouds@123@kingofclouds.fol8o2i.mongodb.net/kingsofcloud?retryWrites=true&w=majority&appName=KingOfClouds"
mongo = PyMongo(app)
fs = GridFS(mongo.db)

client = razorpay.Client(auth=("rzp_test_msxoemlqljagl4", "pQWayIMhE6Jrv9Ncs8oRclQJ"))

@app.route("/")
def hello_world():
    return render_template('index.html')

@app.route("/upload", methods=["POST"])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        file_data = file.read()
        filename = file.filename
        file_id = fs.put(file_data, filename=filename)
        return jsonify({"message": "File uploaded successfully", "file_id": str(file_id)}), 200

@app.route("/get/<file_id>")
def get_image(file_id):
    try:
        file_id = ObjectId(file_id)
        file_data = fs.get(file_id)
        response = BytesIO(file_data.read())
        response.seek(0)
        return send_file(response, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 400

import base64

@app.route("/get_all")
def get_all_images():
    try:
        images = []
        for file in fs.find():
            image_data = file.read()
            image_id = str(file._id)
            # Encode image data to base64
            image_data_base64 = base64.b64encode(image_data).decode('utf-8')
            images.append({"_id": image_id, "data": image_data_base64})
        return jsonify({"images": images})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/delete/<file_id>", methods=["DELETE"])
def delete_image(file_id):
    try:
        # Convert file_id to ObjectId
        file_id = ObjectId(file_id)
        
        # Delete the image from GridFS using the file_id
        fs.delete(file_id)
        
        # Return a success message
        return jsonify({"message": "Image deleted successfully"}), 200
    except Exception as e:
        # If an error occurs, return an error message
        return jsonify({"error": str(e)}), 400

@app.route('/pay', methods=['GET'])
def pay():
    order_id = request.args.get('order_id')
    name = request.args.get('name')
    email = request.args.get('email')
    phone = request.args.get('phone')
    person = request.args.get('person')
    reservation_date = request.args.get('reservation_date')
    reservation_time = request.args.get('reservation_time')
    amount = request.args.get('amount')
    currency = request.args.get('currency')

    # Bundle form data into a variable named pdata
    pdata = {
        'order_id': order_id,
        'name': name,
        'email': email,
        'phone': phone,
        'person': person,
        'reservation_date': reservation_date,
        'reservation_time': reservation_time,
        'amount': amount,
        'currency': currency
    }

    # Render the payment page with the form data bundled in pdata
    return render_template('payment.html', pdata=pdata)


@app.route('/success', methods=["POST"])
def success():
    pid=request.form.get("razorpay_payment_id")
    ordid=request.form.get("razorpay_order_id")
    sign=request.form.get("razorpay_signature")
    print(f"The payment id : {pid}, order id : {ordid} and signature : {sign}")
    params={
    'razorpay_order_id': ordid,
    'razorpay_payment_id': pid,
    'razorpay_signature': sign
    }
    final=client.utility.verify_payment_signature(params)
    if final == True:
        return redirect("/", code=301)
    return "Something Went Wrong Please Try Again"


@app.route('/create_order', methods=['POST'])
def create_order():
    try:
        # Get data from the form
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        person = int(request.form['person'])  # Number of persons
        reservation_date = request.form['reservation-date']
        reservation_time = request.form['reservation-time']
        base_amount_per_person = 2500  # Base amount per person without tax

        # Calculate total amount before tax
        total_amount_before_tax = base_amount_per_person * person

        # Calculate tax (18%)
        tax_rate = 0.18
        tax_amount = total_amount_before_tax * tax_rate

        # Calculate total amount including tax
        total_amount_with_tax = total_amount_before_tax + tax_amount

        # Create order in Razorpay with total amount including tax
        order = client.order.create({
            'amount': total_amount_with_tax * 100,  # Convert to paise (Indian currency)
            'currency': 'INR'
        })

        phone = '+91'+phone

        # Redirect to payment page with order ID and form data as query parameters
        return redirect(url_for('pay', order_id=order['id'],
                                name=name, email=email, phone=phone,
                                person=person, reservation_date=reservation_date,
                                reservation_time=reservation_time, amount=total_amount_with_tax, currency='INR'))

    except Exception as e:
        return jsonify({'error': str(e)}), 400


    
@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    try:
        # Get data from Razorpay webhook
        data = request.get_json()
        payment_id = data['payload']['payment']['entity']['id']
        
        # Fetch payment details
        payment = razorpay_client.payment.fetch(payment_id)
        
        # Verify payment amount and status
        if payment['amount'] == data['payload']['payment']['entity']['amount'] and payment['status'] == 'captured':
            # Payment is valid
            return jsonify({'message': 'Payment successful'}), 200
        else:
            # Payment is invalid
            return jsonify({'error': 'Payment verification failed'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/payment_success', methods=['POST'])
def payment_success():
    try:
        # Parse data from the request
        data = request.json
        order_id = data.get('order_id')
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        amount = data.get('amount')
        person = data.get('person')
        reservation_date = data.get('reservation_date')
        reservation_time = data.get('reservation_time')

        # Access the MongoDB collection
        payments_collection = mongo.db.payments

        # Create a new payment document
        payment_data = {
            'order_id': order_id,
            'name': name,
            'email': email,
            'phone': phone,
            'amount': amount,
            'person': person,
            'reservation_date': reservation_date,
            'reservation_time': reservation_time
        }

        # Insert the payment document into the payments collection
        result = payments_collection.insert_one(payment_data)

        # Check if the insertion was successful
        if result.inserted_id:
            # If data is saved successfully, trigger the notification route
            notify_response = requests.post('http://localhost:5000/send_notifications', json={
                'order_id': order_id,
                'person': person,
                'name': name,
                'phone': phone,
                'email': email,
                'reservation_date': reservation_date,
                'reservation_time': reservation_time
            })

            if notify_response.status_code == 200:
                return jsonify({'message': 'Payment data saved and notifications sent successfully'}), 200
            else:
                return jsonify({'error': 'Failed to send notifications'}), 500
           
        else:
            return jsonify({'error': 'Failed to save payment data'}), 500

    except Exception as e:
        print('payment_success: ' +str(e))
        return jsonify({'error': str(e)}), 400

@app.route('/send_notifications', methods=['POST'])
def send_notifications():
    try:
        data = request.json
        order_id = data.get('order_id'),
        person = data.get('person'),
        name = data.get('name')
        phone = data.get('phone')
        email = data.get('email')
        reservation_date = data.get('reservation_date')
        reservation_time = data.get('reservation_time')

        subject = "Reservation Confirmation"
        message = f"Hello {name},\n\nThank you for choosing our restaurant, which takes dining to new heights! Your reservation for {person} persons on {reservation_date} at {reservation_time} is confirmed. Your order ID is {order_id}. We can't wait to provide you with a thrilling dining experience!"
        send_email(email, message, subject)

        def send_sms():
            sms_message = f"Hello {name}, your reservation for {person} persons on {reservation_date} at {reservation_time} is confirmed! Thank you for choosing us. We look forward to welcoming you!"
            twilio_client.messages.create(body=sms_message, from_='+13344024831', to=phone)

        def send_email_async():
            admin_email = 'info@kingofclouds.in'  # Replace this with the admin's email address
            admin_subject = "New Reservation Notification"
            admin_message = f"New reservation made by {name} for {person} persons on {reservation_date} at {reservation_time}. Order ID: {order_id}."
            send_email(admin_email, admin_message, admin_subject) 

        # Start separate threads for sending SMS and email
        sms_thread = threading.Thread(target=send_sms)
        email_thread = threading.Thread(target=send_email_async)

        sms_thread.start()
        email_thread.start()


        return jsonify({'message': 'Notifications sent successfully'}), 200

    except Exception as e:
        print('send_notifications: ' + str(e) )
        return jsonify({'error': str(e)}), 500


def send_email(to_email, message, subject):
    try:
        msg = MIMEText(message)
        msg['Subject'] = subject
        sender = 'manager@kingofclouds.in'
        msg['From'] = sender
        recipient = to_email
        msg['To'] = recipient
        server = smtplib.SMTP_SSL('smtppro.zoho.in', 465)
        server.login(sender, 'eyJt6NBJBva3')
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return jsonify({'ok': "sent"}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
   
@app.route('/send_otp', methods=['POST'])
def send_otp():
    try:
        # Extract phone number from the request
        phone_number = request.json.get('phone')
        phone_number = '+91'+phone_number

        # Generate a 4-digit OTP
        otp = request.json.get('otp')

        # Compose the SMS message with the OTP
        sms_message = f'Your OTP for verification is: {otp}'

        # Send the SMS using Twilio
        twilio_client.messages.create(body=sms_message, from_='+13344024831', to=phone_number)

        return jsonify({'success': 'ok'}), 200
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
