#encoding:utf-8
from ctypes import resize
from flask import Flask,render_template,jsonify,make_response,request,redirect,jsonify,session,escape,url_for,send_from_directory
from flask.wrappers import Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import FLOAT
from sqlalchemy import and_, or_, not_
import uuid,os,hashlib
from datetime import datetime

startTime=datetime(2021, 10, 25, 18, 00)

class Config:
	basedir = os.path.abspath(os.path.dirname(__file__))
	# SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
	SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:admin@localhost:3306/nazo'
	SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
	SQLALCHEMY_TRACK_MODIFICATIONS=True
app = Flask(__name__)
app.secret_key = 'KALE1D0<3DAHL1A'
app.debug = False
app.config.from_object(Config)
app.add_template_global(round,"round")
db = SQLAlchemy(app)

class Puzzle(db.Model):
	id = db.Column(db.Integer, primary_key=True, nullable=False)
	name = db.Column(db.String(255), index=True, unique=False, nullable=False)
	unlock_score = db.Column(db.Integer, index=False, unique=False, nullable=False)
	score = db.Column(db.Integer, index=False, unique=False, nullable=False)
	tried_num = db.Column(db.Integer, index=False, unique=False, nullable=False)
	passed_num = db.Column(db.Integer, index=False, unique=False, nullable=False)
	author = db.Column(db.String(255), index=True, unique=False, nullable=True)
	answer = db.Column(db.String(255), index=False, unique=False, nullable=False)
	unique_template = db.Column(db.Boolean(), index=False, unique=False, nullable=False)

	def getPassRate(self):
		return '{:.1%}'.format(float(self.passed_num) / (1 if int(self.tried_num) == 0 else int(self.tried_num)))

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	nickname = db.Column(db.String(64), index=True, unique=False)
	email = db.Column(db.String(64), index=True, unique=True)
	password_hash = db.Column(db.String(128), index=False, unique=False)
	credit = db.Column(FLOAT(precision=10, scale=2), index=False, unique=False, nullable=False,default=0)
	passed_num = db.Column(db.Integer, index=False, unique=False, nullable=False,default=0)

	def verifyPassword(self, word):
		return hashlib.md5(word.encode("utf8")).hexdigest() == self.password_hash

	def getData(self):
		data = {}
		data['id'] = self.id
		data['email'] = self.email
		data['nickname'] = self.nickname
		data['credit'] = self.credit
		data['passed'] = self.getPassedPuzzles()
		data['passed_num'] = self.passed_num
		data['progress'] = '{:.0%}'.format(float(len(self.getPassedPuzzles())) / (1 if len(Puzzle.query.all()) == 0 else len(Puzzle.query.all()) - 1))
		return data

	def getPassedPuzzles(self):
		puzzles = Puzzle.query.all()
		passed = []
		for puzzle in puzzles:
			submission = Submission.query.filter_by(user=self.id,puzzle=puzzle.id,accepted=True).first()
			if (submission != None):
				passed.append(puzzle.id)
		return passed

class Submission(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user = db.Column(db.Integer, db.ForeignKey('user.id'), unique=False, nullable=False)
	puzzle = db.Column(db.Integer, db.ForeignKey('puzzle.id'), unique=False, nullable=False)
	accepted = db.Column(db.Boolean, index=False, unique=False, nullable=False)
	create_time=db.Column(db.DateTime, default=datetime.now)

	def getData(self):
		data = {}
		data['user'] = self.user
		data['puzzle'] = self.puzzle
		data['accepted'] = self.accepted
		data['create_time'] = self.create_time
		return data

@app.route('/', methods=['GET'])
def page_index():
	puzzles = Puzzle.query.all()
	if ('user' in session):
		user = User.query.filter_by(email=session['user']['email']).first()
		if (user == None):
			return redirect(url_for('logout'))
		session['user'] = user.getData()
		topUser = User.query.order_by(User.credit.desc()).limit(10)
		top10 = []
		for user in topUser:
			top10.append({'nickname':user.nickname,'email':user.email,'credit':round(user.credit)})
		page = render_template('index.html',user=session['user'],puzzles=puzzles,top10=top10)
	else:
		page = render_template('entry.html')
	response = make_response(page, 200)
	return response

@app.route('/puzzle/<id>', methods=['GET'])
def page_puzzle(id):
	if (not 'user' in session):
		return redirect(url_for('page_index'))
	user = User.query.filter_by(email=session['user']['email']).first()
	puzzle = Puzzle.query.get(int(id))
	if (user.passed_num < puzzle.unlock_score):
		return redirect(url_for('page_index'))
	else:
		# 非通用模板
		if(puzzle.unique_template):
			return render_template('descriptions/%s.html'%(id),puzzle=puzzle)
		else:
			response=make_response(render_template('puzzle.html',puzzle=puzzle))
			# 硬编码- -
			# 如果 userAgent 题目
			if(int(id)==13):
				response.headers['Safe-Token'] = puzzle.answer
			# 如果 cookie 题目
			if(int(id)==14):
				response.set_cookie('isAdmin','false')
			return response

@app.route('/puzzle/<id>/submit', methods=['POST'])
def submit(id):
	if (not 'user' in session):
		return redirect(url_for('page_index'))
	user = User.query.filter_by(email=session['user']['email']).first()
	puzzle = Puzzle.query.get(int(id))
	if (not puzzle == None and judge(int(id),puzzle,request)):
		submission = Submission.query.filter_by(user=user.id,puzzle=puzzle.id,accepted=True).first()
		if (submission == None):
			submission = Submission(user=user.id,puzzle=puzzle.id,accepted=True)

			# ** 取消积分递减规则
			# 获取的分数随着解答出的次数递减，具体系数为 max(0.5,1-x/20)
			# factor=max(0.5,1-puzzle.passed_num/20)
			# user.credit+=factor*puzzle.score

			user.credit+=puzzle.score
			user.passed_num+=1

			puzzle.tried_num = puzzle.tried_num + 1
			puzzle.passed_num = puzzle.passed_num + 1

			db.session.add(submission)
			db.session.commit()
		return jsonify({"success":True,"correct":True})
	else:
		puzzle.tried_num = puzzle.tried_num + 1
		submission = Submission(user=user.id,puzzle=puzzle.id,accepted=False)
		db.session.add(submission)
		db.session.commit()
		return jsonify({"success":True,"correct":False,"message_header":"再试一次吧","message":"答案不正确"})

@app.route('/submission/stat', methods=['GET'])
def stat():
	maxCreditUser=User.query.order_by(User.credit.desc()).first()
	topUser=User.query.filter_by(credit=maxCreditUser.credit).all()
	topUserId=[x.id for x in topUser]
	result=[x.getData() for x in topUser]
	for item in result:
		submission= Submission.query.filter_by(accepted=True).filter_by(user=item['id']).order_by(Submission.create_time.asc()).all()
		totalTime=0
		item['submission']=[]
		for x in submission:
			item['submission'].append(x.getData())
			totalTime+=x.create_time.timestamp()-startTime.timestamp()
		item['totalTime']=totalTime
	result.sort(key=lambda r: r['totalTime'])
	return jsonify({'topUser':result})
	

@app.route('/login', methods=['POST'])
def login():
	if ('user' in session):
		return redirect(url_for('page_index'))
	user = User.query.filter_by(email=request.form['email']).first()
	if (user == None):
		user = User(email=request.form['email'], nickname=request.form['nickname'],password_hash=hashlib.md5(request.form['password'].encode("utf8")).hexdigest())
		db.session.add(user)
		session['user'] = user.getData()
	else:
		if (user.verifyPassword(request.form['password'])):
			if(request.form['nickname']):
				user.nickname = request.form['nickname']
			session['user'] = user.getData()
		else:
			return "<html><body><script type='text/javascript'>alert('您输入的密码与初设密码不符，验证无法通过！');window.location.href='/';</script></body></html>"
	db.session.commit()
	return redirect(url_for('page_index'))

@app.route('/logout', methods=['GET'])
def logout():
	session.pop('user')
	return redirect(url_for('page_index'))

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('assets/img/favicon.ico')
	
def judge(id,puzzle,request):
	if(id==13):
		userAgent=request.headers.get('User-Agent')
		return 'mucfc' in userAgent or 'MUCFC' in userAgent
	if(id==14):
		isAdmin=request.cookies.get("isAdmin")
		return isAdmin=='true'
	return puzzle.answer == request.form['answer']

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=80)
