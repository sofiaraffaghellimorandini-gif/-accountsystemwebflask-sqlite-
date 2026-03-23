from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accounting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class AccountState(db.Model):
    __tablename__ = 'account_state'

    id = db.Column(db.Integer, primary_key=True)
    stock = db.Column(db.Integer, nullable=False, default=0)
    balance = db.Column(db.Float, nullable=False, default=0.0)


class Transaction(db.Model):
    __tablename__ = 'transaction'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime_str = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    product = db.Column(db.String, nullable=False)
    quantity = db.Column(db.String, nullable=False)
    unit_price = db.Column(db.String, nullable=False)
    total = db.Column(db.Float, nullable=False)


def get_account_state():
    state = db.session.get(AccountState, 1)
    if state is None:
        state = AccountState(id=1, stock=100, balance=10000.0)
        db.session.add(state)
        db.session.commit()
    return state


def add_to_history(transaction_type, product, quantity, unit_price, total):
    try:
        entry = Transaction(
            datetime_str=datetime.now().strftime('%Y-%m-%d %H:%M'),
            type=transaction_type,
            product=product,
            quantity=str(quantity),
            unit_price=str(unit_price),
            total=total
        )
        db.session.add(entry)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        return False


@app.route('/')
def index():
    try:
        state = get_account_state()
        return render_template('index.html', stock=state.stock, balance=state.balance)
    except SQLAlchemyError as e:
        flash(f'Error: Could not load account data — {e}', 'error')
        return render_template('index.html', stock=0, balance=0.0)


@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    if request.method == 'POST':
        try:
            product_name = request.form.get('product_name', '').strip()
            unit_price = request.form.get('unit_price', '')
            quantity = request.form.get('quantity', '')

            if not product_name:
                flash('Error: Product name is required.', 'error')
                return redirect(url_for('purchase'))

            try:
                unit_price = float(unit_price)
                if unit_price <= 0:
                    flash('Error: Unit price must be greater than 0.', 'error')
                    return redirect(url_for('purchase'))
            except ValueError:
                flash('Error: Unit price must be a valid number.', 'error')
                return redirect(url_for('purchase'))

            try:
                quantity = int(quantity)
                if quantity <= 0:
                    flash('Error: Quantity must be greater than 0.', 'error')
                    return redirect(url_for('purchase'))
            except ValueError:
                flash('Error: Quantity must be a valid whole number.', 'error')
                return redirect(url_for('purchase'))

            total_cost = unit_price * quantity
            state = get_account_state()

            if state.balance < total_cost:
                flash(f'Error: Insufficient balance. You need ${total_cost:.2f} but only have ${state.balance:.2f}.', 'error')
                return redirect(url_for('purchase'))

            state.stock += quantity
            state.balance -= total_cost
            db.session.commit()

            if add_to_history('Purchase', product_name, quantity, unit_price, total_cost):
                flash(f'Success! Purchased {quantity} x {product_name} for ${total_cost:.2f}.', 'success')
            else:
                flash('Error: Could not save transaction history.', 'error')

            return redirect(url_for('index'))

        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error: Database error — {e}', 'error')
            return redirect(url_for('purchase'))
        except Exception as e:
            flash(f'Error: An unexpected error occurred: {str(e)}', 'error')
            return redirect(url_for('purchase'))

    return render_template('purchase.html')


@app.route('/sale', methods=['GET', 'POST'])
def sale():
    if request.method == 'POST':
        try:
            product_name = request.form.get('product_name', '').strip()
            unit_price = request.form.get('unit_price', '')
            quantity = request.form.get('quantity', '')

            if not product_name:
                flash('Error: Product name is required.', 'error')
                return redirect(url_for('sale'))

            try:
                unit_price = float(unit_price)
                if unit_price <= 0:
                    flash('Error: Unit price must be greater than 0.', 'error')
                    return redirect(url_for('sale'))
            except ValueError:
                flash('Error: Unit price must be a valid number.', 'error')
                return redirect(url_for('sale'))

            try:
                quantity = int(quantity)
                if quantity <= 0:
                    flash('Error: Quantity must be greater than 0.', 'error')
                    return redirect(url_for('sale'))
            except ValueError:
                flash('Error: Quantity must be a valid whole number.', 'error')
                return redirect(url_for('sale'))

            total_revenue = unit_price * quantity
            state = get_account_state()

            if state.stock < quantity:
                flash(f'Error: Insufficient stock. You have {state.stock} units but trying to sell {quantity}.', 'error')
                return redirect(url_for('sale'))

            state.stock -= quantity
            state.balance += total_revenue
            db.session.commit()

            if add_to_history('Sale', product_name, quantity, unit_price, total_revenue):
                flash(f'Success! Sold {quantity} x {product_name} for ${total_revenue:.2f}.', 'success')
            else:
                flash('Error: Could not save transaction history.', 'error')

            return redirect(url_for('index'))

        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error: Database error — {e}', 'error')
            return redirect(url_for('sale'))
        except Exception as e:
            flash(f'Error: An unexpected error occurred: {str(e)}', 'error')
            return redirect(url_for('sale'))

    return render_template('sale.html')


@app.route('/balance_change', methods=['GET', 'POST'])
def balance_change():
    if request.method == 'POST':
        try:
            operation_type = request.form.get('operation_type', '')
            amount = request.form.get('amount', '')

            if operation_type not in ['add', 'subtract']:
                flash('Error: Please select a valid operation type.', 'error')
                return redirect(url_for('balance_change'))

            try:
                amount = float(amount)
                if amount <= 0:
                    flash('Error: Amount must be greater than 0.', 'error')
                    return redirect(url_for('balance_change'))
            except ValueError:
                flash('Error: Amount must be a valid number.', 'error')
                return redirect(url_for('balance_change'))

            state = get_account_state()

            if operation_type == 'add':
                state.balance += amount
                operation_display = 'Add'
            else:
                if state.balance < amount:
                    flash(f'Error: Insufficient balance. You have ${state.balance:.2f} but trying to subtract ${amount:.2f}.', 'error')
                    return redirect(url_for('balance_change'))
                state.balance -= amount
                operation_display = 'Subtract'

            db.session.commit()

            if add_to_history('Balance Change', 'N/A', 'N/A', operation_display, amount):
                flash(f'Success! {operation_display}ed ${amount:.2f} to balance.', 'success')
            else:
                flash('Error: Could not save transaction history.', 'error')

            return redirect(url_for('index'))

        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error: Database error — {e}', 'error')
            return redirect(url_for('balance_change'))
        except Exception as e:
            flash(f'Error: An unexpected error occurred: {str(e)}', 'error')
            return redirect(url_for('balance_change'))

    return render_template('balance_change.html')


@app.route('/history/')
@app.route('/history/<int:line_from>/<int:line_to>/')
def history(line_from=None, line_to=None):
    try:
        query = Transaction.query.order_by(Transaction.id)
        all_count = query.count()

        if line_from is None and line_to is None:
            transactions = query.all()
            showing_range = False
        else:
            line_from = max(0, line_from)
            line_to = min(line_to, all_count)
            if line_from > line_to:
                line_from, line_to = line_to, line_from

            transactions = query.offset(line_from).limit(line_to - line_from).all()
            showing_range = True

        history_list = [
            {
                'datetime': t.datetime_str,
                'type': t.type,
                'product': t.product,
                'quantity': t.quantity,
                'unit_price': t.unit_price,
                'total': t.total,
            }
            for t in transactions
        ]

        return render_template('history.html',
                               history=history_list,
                               total_entries=all_count,
                               showing_range=showing_range,
                               line_from=line_from,
                               line_to=line_to)

    except SQLAlchemyError as e:
        flash(f'Error: Could not load history — {e}', 'error')
        return render_template('history.html', history=[], total_entries=0,
                               showing_range=False, line_from=None, line_to=None)


@app.route('/history/filter', methods=['POST'])
def history_filter():
    try:
        line_from = request.form.get('line_from', '')
        line_to = request.form.get('line_to', '')

        if not line_from and not line_to:
            return redirect(url_for('history'))

        try:
            line_from = int(line_from) if line_from else 0
            line_to = int(line_to) if line_to else Transaction.query.count()
        except ValueError:
            flash('Error: Line numbers must be valid integers.', 'error')
            return redirect(url_for('history'))

        return redirect(url_for('history', line_from=line_from, line_to=line_to))

    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('history'))


with app.app_context():
    db.create_all()
    get_account_state()

if __name__ == '__main__':
    app.run(debug=True)
