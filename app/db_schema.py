"""SQL schema reference used in classifier and SQL-generation prompts."""

FLIGHTS_TABLE_SCHEMA = """
Database table: flights

Column Name      | Data Type  | Description
-----------------+------------+-------------------------------------------
id               | BIGINT     | Unique identifier for each flight record (PK)
flight_no        | TEXT       | Flight number (e.g., AI695, SG528)
airline_code     | TEXT       | Airline code (e.g., AI, SG, IX)
airline_name     | TEXT       | Full airline name
origin           | TEXT       | Origin airport code (e.g., DEL, BOM, BLR)
destination      | TEXT       | Destination airport code
departure_date   | DATE       | Scheduled departure date (YYYY-MM-DD)
departure_time   | TIME       | Scheduled departure time
arrival_date     | DATE       | Scheduled arrival date
arrival_time     | TIME       | Scheduled arrival time
status           | TEXT       | On Time, Delayed, or Cancelled
delay_minutes    | INTEGER    | Delay duration in minutes
delay_reason     | TEXT       | Reason for delay, if applicable
terminal         | TEXT       | Departure terminal
gate             | TEXT       | Departure gate number
aircraft_type    | TEXT       | Aircraft model
seats_total      | INTEGER    | Total seats available
seats_booked     | INTEGER    | Seats already booked
fare_inr         | INTEGER    | Ticket fare in Indian Rupees

NOT available in this table: PNR, booking reference, passenger name, email, phone, or customer records.
"""
