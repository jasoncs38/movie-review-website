import os
import secrets
from PIL import Image,ImageOps
from flask import render_template,flash,redirect,url_for,request,abort
from moviesite import app,db,bcrypt,mail
from moviesite.forms import RegistrationForm,LoginForm,UpdateAccountForm,ReviewForm,AddMovieForm,RequestResetForm,ResetPasswordForm
from moviesite.models import User,Review,Movie
from flask_login import login_user,logout_user,current_user,login_required
from flask_mail import Message



@app.route("/")
@app.route("/home")
def home():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "")
    query = Movie.query
    if search:
        query = query.filter(Movie.title.ilike(f"%{search}%"))
    movies = query.order_by(Movie.release_year.desc()).paginate(page=page, per_page=10)
    return render_template("home.html",title="Home",movies=movies,search=search)

@app.route("/about")
def about():
    return render_template("about.html",title="About")

@app.route("/register",methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form=RegistrationForm()
    if form.validate_on_submit():
        hashed_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user=User(username=form.username.data,
                  email=form.email.data,password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f' Your account has been created. You are now able to log in.','success')
        return redirect (url_for('login'))
    return render_template("register.html",title="Register",form=form)

@app.route("/login",methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form=LoginForm()
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user,remember=form.remember.data)
            flash(f'Welcome { user.username}!','success')
            next_page=request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Unsuccesful Login. Please check email and password.','danger')
    return render_template("login.html",title="Login",form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_profile_picture(form_picture):
   random_hex=secrets.token_hex(8)
   _,f_ext=os.path.splitext(form_picture.filename)
   picture_fn= random_hex + f_ext
   picture_path=os.path.join(app.root_path,'static/profile_pics',picture_fn)

   output_size=(125,125)
   image = Image.open(form_picture)
   image = ImageOps.exif_transpose(image)
   image = ImageOps.fit(image,output_size,Image.Resampling.LANCZOS)
   image.save(picture_path)

   return picture_fn

@app.route("/account",methods=['GET','POST'])
@login_required
def account():
    form=UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file=save_profile_picture(form.picture.data)
            current_user.image_file=picture_file

        current_user.username=form.username.data
        current_user.email=form.email.data
        db.session.commit()
        flash('Your account has been updated.','success')
        return redirect(url_for('account'))
    elif request.method=='GET':
        form.username.data=current_user.username
        form.email.data=current_user.email
    image_file=url_for('static',filename='profile_pics/'+current_user.image_file)
    return render_template("account.html",title="Account",
                           form=form,image_file=image_file)


def save_picture(form_picture):
    random_hex=secrets.token_hex(8)
    _, f_ext=os.path.splitext(form_picture.filename)
    picture_fn=random_hex+f_ext
    picture_path=os.path.join(app.root_path,'static/posters',picture_fn)


    i=Image.open(form_picture)
    i.save(picture_path)

    return picture_fn

@app.route("/movie/new",methods=['GET','POST'])
@login_required
def add_movie():
    form=AddMovieForm()
    if form.validate_on_submit():
        movie=Movie(title=form.title.data,
                release_year=form.release_year.data,
                genre=form.genre.data,
                description=form.description.data)
        if form.poster.data:
            picture_file=save_picture(form.poster.data)
            movie.poster=picture_file
        db.session.add(movie)
        db.session.commit()
        flash('Movie has been added successfully.','success')
        return redirect(url_for('home'))
    return render_template("add_movie.html",title="Add Movie",form=form)

@app.route("/movie/<int:movie_id>")
def movie_page(movie_id):
    movie=Movie.query.get_or_404(movie_id)
    page = request.args.get("page", 1, type=int)
    reviews = Review.query.filter_by(movie_id=movie.id)\
        .order_by(Review.date_posted.desc())\
        .paginate(page=page, per_page=10)
    if current_user.is_authenticated:
        existing_review = Review.query.filter_by(
            user_id=current_user.id,
            movie_id=movie.id).first()
    else:
        existing_review = None
      
    if movie.reviews:
        average_rating = (
            sum(review.rating for review in movie.reviews)
            / len(movie.reviews)
        )
    else:
        average_rating = 0     
    return render_template("movie_page.html",reviews=reviews,movie=movie,
                           average_rating=average_rating,
                           existing_review=existing_review)

@app.route("/movie/<int:movie_id>/review", methods=['GET', 'POST'])
@login_required
def write_review(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    existing_review = Review.query.filter_by(
        user_id=current_user.id,
        movie_id=movie.id).first()
    form = ReviewForm()
    if request.method == "GET" and existing_review:
        form.rating.data = existing_review.rating
        form.content.data = existing_review.content
    if form.validate_on_submit():
        if existing_review:
            existing_review.rating = form.rating.data
            existing_review.content = form.content.data
            flash("Your review has been updated!", "success")
        else:
            review = Review(content=form.content.data,rating=form.rating.data,
                            user_id=current_user.id,movie_id=movie.id)
            db.session.add(review)
            flash("Your review has been added!", "success")
        db.session.commit()
        return redirect(url_for("movie_page", movie_id=movie.id))

    return render_template("write_review.html",form=form,movie=movie,
                           existing_review=existing_review)
         

@app.route("/review/<int:review_id>/delete",methods=['POST'])
@login_required
def delete_review(review_id):
    review=Review.query.get_or_404(review_id)
    if review.author!=current_user:
        abort(403)
    db.session.delete(review)
    db.session.commit()
    flash('Your review has been deleted!','success')
    return redirect(url_for('movie_page',movie_id=review.movie_id))


@app.route("/user/<string:username>")
def user_profile(username):
    user=User.query.filter_by(username=username).first_or_404()
    image_file=url_for('static',filename='profile_pics/'+user.image_file)
    page = request.args.get("page", 1, type=int)
    user_reviews = Review.query.filter_by(author=user)\
    .order_by(Review.date_posted.desc())\
    .paginate(page=page, per_page=10)
    all_reviews = user.reviews
    if all_reviews:
     average_rating = (
        sum(review.rating for review in all_reviews)
        / len(all_reviews))
    else:
        average_rating = 0
    return render_template("user_profile.html",user=user,
                           image_file=image_file,user_reviews=user_reviews,
                           average_rating=average_rating)


@app.route("/admin",methods=['GET','POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
    page=request.args.get('page',1,type=int)
    q = request.args.get("q", "")
    query = Movie.query
    if q:
        query = query.filter(Movie.title.ilike(f"%{q}%"))
    movies=query.order_by(Movie.release_year.desc()).paginate(page=page, per_page=10)
    movie_count=Movie.query.count()
    review_count=Review.query.count()
    user_count=User.query.count()
    image_file=url_for('static',filename='profile_pics/'+current_user.image_file)

    return render_template("admin_dashboard.html",movies=movies,q=q,
                           image_file=image_file,movie_count=movie_count,
                           review_count=review_count,user_count=user_count)

@app.route("/admin/movie/<int:movie_id>/edit",methods=['GET','POST'])
@login_required
def edit_movie(movie_id):
    if not current_user.is_admin:
        abort(403)
    movie=Movie.query.get_or_404(movie_id)
    form=AddMovieForm()
    if request.method=='GET':
        form.title.data=movie.title
        form.release_year.data=movie.release_year
        form.genre.data=movie.genre
        form.description.data=movie.description
    if form.validate_on_submit():
            movie.title=form.title.data
            movie.release_year=form.release_year.data
            movie.genre=form.genre.data
            movie.description=form.description.data
            if form.poster.data:
                picture=save_picture(form.poster.data)
                movie.poster=picture
            db.session.commit()
            flash('Movie has been updated!','success')
            return redirect(url_for('admin_dashboard'))
    return render_template("add_movie.html",form=form,movie=movie,legend='Update Movie')

@app.route("/admin/movie/<int:movie_id>/delete",methods=['POST'])
@login_required
def delete_movie(movie_id):
    if not current_user.is_admin:
        abort(403)
    movie=Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()
    flash('Movie has been deleted!','success')
    return redirect(url_for('admin_dashboard'))    
    
            

def send_reset_email(user):
    token=user.get_reset_token()
    msg=Message('Password Reset Request',
                sender='noreply@demo.com',
                recipients=[user.email])
    msg.body=f'''To reset your password, visit the following link:
{url_for('reset_token',token=token,_external=True)}

If you did not make this request then simply ignore this email and no change will be made.

'''
    mail.send(msg)


@app.route("/reset_password",methods=['GET','POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form=RequestResetForm()  
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password. Please check your email.','info')
        return redirect(url_for('login'))
    return render_template('reset_request.html',title='Reset Password',form=form) 

@app.route("/reset_password/<token>",methods=['GET','POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user=User.verify_reset_token(token)
    if user is None:
        flash('Invalid or expired token.','warning')
        return redirect(url_for('reset_request'))
    form=ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password=hashed_password
        db.session.commit()
        flash('Your password has been updated! You can now log in.','success')
        return redirect(url_for('login'))
    return render_template('reset_token.html',title='Reset password',form=form)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('errors/404.html'),404

@app.errorhandler(403)
def forbidden_action(error):
    return render_template('errors/403.html'),403

@app.errorhandler(500)
def general_error(error):
    return render_template('errors/500.html'),500


