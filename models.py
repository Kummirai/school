import psycopg2
import psycopg2.extras
from psycopg2.extras import DictCursor
import os

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv('host'),
            database=os.getenv('dbname'),
            user=os.getenv('user'),
            password=os.getenv('password'),
            port=os.getenv('5432'),
            # sslmode='require'
        )
        print("✅ Successfully connected to Database!")
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        raise

def initialize_database():
    conn = get_db_connection()
    cur = conn.cursor()

    # Add this after your other table creations
    cur.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS parent_students (
        parent_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        PRIMARY KEY (parent_id, student_id)
    )
''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS saved_equations (
            id SERIAL PRIMARY KEY ,
            user_id INTEGER NOT NULL,
            equation TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id SERIAL PRIMARY KEY,
            user_name VARCHAR(100) NOT NULL,
            user_email VARCHAR(100) NOT NULL,
            user_phone VARCHAR(20) NOT NULL,
            plan_id INTEGER NOT NULL,
            plan_name VARCHAR(50) NOT NULL,
            plan_price NUMERIC(10,2) NOT NULL,
            message TEXT,
            status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
            request_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            admin_notes TEXT,
            processed_date TIMESTAMP WITH TIME ZONE
            CONSTRAINT valid_email CHECK (user_email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$')
        );
                ''')

    # Add these tables after your other table creations
    cur.execute('''
        CREATE TABLE IF NOT EXISTS session_requests (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            category VARCHAR(100),
            preferred_time TIMESTAMP,
            status VARCHAR(50) DEFAULT 'pending',  -- pending, approved, rejected
            admin_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS session_request_notes (
            id SERIAL PRIMARY KEY,
            request_id INTEGER NOT NULL REFERENCES session_requests(id) ON DELETE CASCADE,
            admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_announcements (
            announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            is_read BOOLEAN DEFAULT FALSE,
            read_at TIMESTAMP,
            PRIMARY KEY (announcement_id, user_id)
        )
    ''')

    # Create users table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role VARCHAR(50) NOT NULL
    )
    ''')

    # Subscription tables
    cur.execute('''
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            duration_days INTEGER NOT NULL
        )
    ''')

    cur.execute('''
            CREATE TABLE IF NOT EXISTS exam_results (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                exam_id INTEGER NOT NULL, -- Storing the JSON exam ID
                score DECIMAL(5,2) NOT NULL, -- Store score as a percentage or points
                total_questions INTEGER NOT NULL,
                completion_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            plan_id INTEGER NOT NULL REFERENCES subscription_plans(id) ON DELETE CASCADE,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT FALSE,
            payment_status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            subscription_id INTEGER NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
            amount DECIMAL(10,2) NOT NULL,
            payment_date TIMESTAMP NOT NULL,
            transaction_id VARCHAR(255),
            status VARCHAR(50) NOT NULL,
            receipt_url VARCHAR(255)
        )
    ''')

    # Create tutorial_categories table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tutorial_categories (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL
    )
    ''')

    # Add these new tables for assignment system
    cur.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            subject VARCHAR(100),
            total_marks INTEGER,
            deadline TIMESTAMP,
            content TEXT, -- For interactive content or complex structures
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id SERIAL PRIMARY KEY,
            assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            submission_text TEXT,
            file_path VARCHAR(255), -- Path to uploaded file if any
            submission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            grade INTEGER, -- Nullable, will be set after grading
            feedback TEXT, -- Teacher feedback
            interactive_submission_data JSONB, -- For structured/interactive answers
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_assignment_student_submission UNIQUE (assignment_id, student_id)
        );
    ''')

    # Add this to the initialize_database() function
    cur.execute('''
        CREATE TABLE IF NOT EXISTS practice_scores (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject VARCHAR(50) NOT NULL,
            topic VARCHAR(100) NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_practice_attempt UNIQUE (student_id, subject, topic)
        )
    ''')

    # Add this new table for assignment-user relationships
    cur.execute('''
        CREATE TABLE IF NOT EXISTS assignment_students (
            assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (assignment_id, user_id)
        )
    ''')

    # Create tutorial_videos table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tutorial_videos (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        url TEXT NOT NULL,
        category_id INTEGER NOT NULL REFERENCES tutorial_categories(id) ON DELETE CASCADE
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS student_activities (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL,
        activity_type VARCHAR(100) NOT NULL,
        description TEXT,
        icon VARCHAR(50) DEFAULT 'check',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # Create tutorial_sessions table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tutorial_sessions (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP NOT NULL,
        max_students INTEGER NOT NULL
    )
    ''')

    # Create student_bookings table
    # In your initialize_database() function
    cur.execute('''
    CREATE TABLE IF NOT EXISTS student_bookings (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        session_id INTEGER NOT NULL REFERENCES tutorial_sessions(id) ON DELETE CASCADE,
        booking_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) DEFAULT 'confirmed',
        CONSTRAINT unique_booking UNIQUE (student_id, session_id)
    )
    ''')

    conn.commit()

    # >>> ADDED: Check if subscription plans exist before inserting defaults
    cur.execute('SELECT COUNT(*) FROM subscription_plans')
    plan_count = cur.fetchone()[0]

    if plan_count == 0:
        # Insert default subscription plans if they don't exist
        cur.execute('''
            INSERT INTO subscription_plans (name, description, price, duration_days)
            VALUES
                ('Access', 'Access to core tutorials and study guides', 99.99, 30),
                ('Premium', 'All features including priority support', 199.99, 30),
                ('Standard', 'Access to core tutorials, study guides and Exams', 149.99, 30),

        ''')
        conn.commit()  # Commit is done once at the end
        print("✅ Default subscription plans inserted.")
    else:
        print("Subscription plans already exist, skipping default insert.")
    # <<< END ADDED

    # Check if there are any users
    cur.execute('SELECT COUNT(*) FROM users')
    user_count = cur.fetchone()[0]

    if user_count == 0:
        # Insert default admin user
        default_admin_username = 'admin'
        default_admin_password = generate_password_hash('admin123')
        cur.execute('''
            INSERT INTO users (username, password, role)
            VALUES (%s, %s, %s)
        ''', (default_admin_username, default_admin_password, 'admin'))
        conn.commit()
        print("✅ Default admin user created: admin / admin123")

    cur.close()
    conn.close()
