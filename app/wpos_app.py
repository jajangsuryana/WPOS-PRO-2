import os,sys,sqlite3,hashlib,secrets,shutil,datetime,tkinter as tk
from tkinter import ttk,messagebox,simpledialog
APP='WPOS PRO 2'
def app_dir(): return os.path.dirname(sys.executable) if getattr(sys,'frozen',False) else os.path.dirname(os.path.abspath(__file__))
def db_path():
 p=os.path.join(app_dir(),'wpos.db')
 return p if os.path.exists(p) else os.path.join(os.path.dirname(app_dir()),'wpos.db')
def connect():
 c=sqlite3.connect(db_path());c.row_factory=sqlite3.Row;return c
def make_password(password,iters=210000):
 salt=secrets.token_hex(16);h=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),iters).hex()
 return 'pbkdf2_sha256$%d$%s$%s' % (iters,salt,h)
def verify(password,encoded):
 try:
  a,s,d=encoded.split('$')[1:];h=hashlib.pbkdf2_hmac('sha256',password.encode(),s.encode(),int(a)).hex();return secrets.compare_digest(h,d)
 except Exception:return False
def backup_db():
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out=os.path.join(app_dir(),f'wpos_backup_{stamp}.db');shutil.copy2(db_path(),out);return out

class ResetTool(tk.Toplevel):
 def __init__(self,parent):
  super().__init__(parent);self.title('WPOS Password Reset');self.geometry('620x440')
  f=tk.Frame(self,bg='white',padx=24,pady=24);f.pack(fill='both',expand=True,padx=18,pady=18)
  tk.Label(f,text='Password Reset Center',font=('Segoe UI',20,'bold'),bg='white',fg='#15233d').pack(anchor='w')
  tk.Label(f,text='Backup otomatis dibuat sebelum perubahan.',bg='white',fg='#66758b').pack(anchor='w',pady=(4,18))
  self.t=ttk.Treeview(f,columns=('u','n','r','a'),show='headings',height=9)
  for c,h,w in [('u','Username',120),('n','Nama',210),('r','Role',90),('a','Status',80)]:self.t.heading(c,text=h);self.t.column(c,width=w)
  self.t.pack(fill='x');self.load()
  tk.Button(f,text='Reset Password',command=self.reset,bg='#172a4d',fg='white',relief='flat',padx=18,pady=9).pack(side='left',pady=18)
 def load(self):
  self.t.delete(*self.t.get_children())
  with connect() as c:
   for r in c.execute('select username,name,role,active from users order by id'):self.t.insert('','end',values=(r['username'],r['name'],r['role'],'Aktif' if r['active'] else 'Nonaktif'))
 def reset(self):
  i=self.t.focus()
  if not i:return messagebox.showwarning('Reset','Pilih akun.')
  u=self.t.item(i,'values')[0];p=simpledialog.askstring('Password baru',f'Password baru untuk {u}:',show='•',parent=self)
  if not p:return
  if len(p)<6:return messagebox.showwarning('Password','Minimal 6 karakter.')
  q=simpledialog.askstring('Konfirmasi','Ulangi password:',show='•',parent=self)
  if p!=q:return messagebox.showerror('Password','Konfirmasi tidak cocok.')
  try:
   b=backup_db()
   with connect() as c:c.execute('update users set password_hash=? where username=?',(make_password(p),u));c.commit()
   messagebox.showinfo('Berhasil',f'Password {u} diubah. Backup: {b}');self.load()
  except Exception as e:messagebox.showerror('Reset gagal',str(e))

class POS(tk.Toplevel):
 def __init__(self,root,user):
  super().__init__(root);self.root=root;self.user=user;self.cart=[];self.title(APP);self.geometry('1080x700')
  top=tk.Frame(self,bg='#0f1b33',height=64);top.pack(fill='x');top.pack_propagate(False)
  tk.Label(top,text=APP,font=('Segoe UI',18,'bold'),fg='white',bg='#0f1b33').pack(side='left',padx=22)
  tk.Label(top,text=f'{user["name"] or user["username"]} • {user["role"]}',fg='white',bg='#0f1b33').pack(side='right',padx=22)
  body=tk.Frame(self,padx=16,pady=16);body.pack(fill='both',expand=True)
  l=tk.Frame(body,bg='white',padx=14,pady=14);l.pack(side='left',fill='both',expand=True,padx=(0,9))
  r=tk.Frame(body,bg='white',padx=14,pady=14,width=350);r.pack(side='right',fill='y');r.pack_propagate(False)
  tk.Label(l,text='Kasir',font=('Segoe UI',18,'bold'),bg='white').pack(anchor='w')
  self.q=ttk.Entry(l);self.q.pack(fill='x',pady=9,ipady=6);self.q.bind('<KeyRelease>',lambda e:self.products())
  self.pt=ttk.Treeview(l,columns=('b','n','p','s'),show='headings')
  for c,h,w in [('b','Barcode',120),('n','Produk',270),('p','Harga',120),('s','Stok',70)]:self.pt.heading(c,text=h);self.pt.column(c,width=w)
  self.pt.pack(fill='both',expand=True);self.pt.bind('<Double-1>',lambda e:self.add())
  tk.Button(l,text='Tambah',command=self.add,bg='#172a4d',fg='white',relief='flat',pady=8).pack(anchor='e',pady=8)
  tk.Label(r,text='Keranjang',font=('Segoe UI',18,'bold'),bg='white').pack(anchor='w')
  self.ct=ttk.Treeview(r,columns=('n','q','t'),show='headings',height=16)
  for c,h,w in [('n','Produk',145),('q','Qty',45),('t','Total',110)]:self.ct.heading(c,text=h);self.ct.column(c,width=w)
  self.ct.pack(fill='x',pady=9);self.total=tk.Label(r,text='Rp 0',font=('Segoe UI',21,'bold'),bg='white');self.total.pack(anchor='e',pady=8)
  tk.Button(r,text='CHECKOUT',command=self.checkout,bg='#087a53',fg='white',relief='flat',pady=11).pack(fill='x')
  tk.Button(r,text='Password Reset Center',command=lambda:ResetTool(self),relief='flat',pady=7).pack(fill='x',pady=7);self.products()
 def products(self):
  q=self.q.get().strip();self.pt.delete(*self.pt.get_children())
  with connect() as c:rows=c.execute("select barcode,name,selling_price,stock from products where active=1 and (barcode like ? or name like ?) order by name limit 300",(f'%{q}%',f'%{q}%')).fetchall()
  for x in rows:self.pt.insert('','end',values=(x['barcode'],x['name'],f'Rp {x["selling_price"]:,.0f}',x['stock']))
 def add(self):
  i=self.pt.focus()
  if not i:return
  barcode=self.pt.item(i,'values')[0]
  with connect() as c:x=c.execute('select * from products where barcode=?',(barcode,)).fetchone()
  for z in self.cart:
   if z['id']==x['id']:z['qty']+=1;break
  else:self.cart.append({'id':x['id'],'name':x['name'],'price':float(x['selling_price']),'qty':1})
  self.refresh()
 def refresh(self):
  self.ct.delete(*self.ct.get_children());total=0
  for x in self.cart:
   v=x['price']*x['qty'];total+=v;self.ct.insert('','end',values=(x['name'],x['qty'],f'Rp {v:,.0f}'))
  self.total.config(text=f'Rp {total:,.0f}')
 def checkout(self):
  if not self.cart:return messagebox.showwarning('Kasir','Keranjang kosong.')
  total=sum(x['price']*x['qty'] for x in self.cart);paid=simpledialog.askfloat('Pembayaran',f'Total Rp {total:,.0f}\nUang dibayar:',parent=self,minvalue=total)
  if paid is None:return
  now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S');inv='INV-'+datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
  try:
   with connect() as c:
    c.execute('begin');c.execute('insert into sales(invoice_no,created_at,subtotal,discount,total,paid,change,payment_method) values(?,?,?,?,?,?,?,?)',(inv,now,total,0,total,paid,paid-total,'CASH'));sid=c.execute('select last_insert_rowid()').fetchone()[0]
    for x in self.cart:
     stock=c.execute('select stock from products where id=?',(x['id'],)).fetchone()[0]
     if stock<x['qty']:raise ValueError(f'Stok {x["name"]} tidak cukup.')
     c.execute('insert into sale_items(sale_id,product_id,quantity,unit_price,discount,line_total) values(?,?,?,?,?,?)',(sid,x['id'],x['qty'],x['price'],0,x['qty']*x['price']))
     c.execute('update products set stock=stock-? where id=?',(x['qty'],x['id']));c.execute('insert into stock_movements(product_id,movement_type,quantity,reference,created_at) values(?,?,?,?,?)',(x['id'],'SALE',-x['qty'],inv,now))
    c.commit()
   messagebox.showinfo('Berhasil',f'{inv}\nKembalian Rp {paid-total:,.0f}');self.cart=[];self.refresh();self.products()
  except Exception as e:messagebox.showerror('Transaksi gagal',str(e))

class Login(tk.Tk):
 def __init__(self):
  super().__init__();self.title(APP);self.geometry('460x410');self.resizable(False,False)
  f=tk.Frame(self,bg='#111a2e',padx=35,pady=28);f.place(relx=.5,rely=.5,anchor='center',relwidth=.84,relheight=.84)
  tk.Label(f,text=APP,font=('Segoe UI',23,'bold'),fg='white',bg='#111a2e').pack(pady=(5,2));tk.Label(f,text='Point of Sale • Offline SQLite',fg='#9fb0ca',bg='#111a2e').pack(pady=(0,20))
  tk.Label(f,text='Username',fg='white',bg='#111a2e').pack(anchor='w');self.u=ttk.Entry(f);self.u.pack(fill='x',ipady=6,pady=(3,10))
  tk.Label(f,text='Password',fg='white',bg='#111a2e').pack(anchor='w');self.p=ttk.Entry(f,show='•');self.p.pack(fill='x',ipady=6,pady=(3,14));self.p.bind('<Return>',lambda e:self.login())
  ttk.Button(f,text='MASUK',command=self.login).pack(fill='x',ipady=7);ttk.Button(f,text='Lupa Password / Reset',command=lambda:ResetTool(self)).pack(fill='x',pady=9)
 def login(self):
  try:
   with connect() as c:r=c.execute('select * from users where username=? and active=1',(self.u.get().strip(),)).fetchone()
   if not r or not verify(self.p.get(),r['password_hash']):return messagebox.showerror('Login gagal','Username atau password salah.')
   self.withdraw();POS(self,dict(r))
  except Exception as e:messagebox.showerror('Database error',str(e))

if __name__=='__main__':
 if not os.path.exists(db_path()):messagebox.showerror('Database tidak ditemukan','Letakkan wpos.db di samping EXE.');raise SystemExit(1)
 Login().mainloop()
