import os,sqlite3,hashlib,secrets,shutil,datetime,csv,tempfile,sys
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog,filedialog

APP="WPOS PRO 2"
ROOT=os.path.dirname(os.path.abspath(sys.executable if getattr(sys,"frozen",False) else __file__))
DB=os.path.join(ROOT,"wpos.db")

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def pw_hash(p,it=210000):
    salt=secrets.token_hex(16); h=hashlib.pbkdf2_hmac("sha256",p.encode(),salt.encode(),it).hex()
    return "pbkdf2_sha256$"+str(it)+"$"+salt+"$"+h
def pw_ok(p,x):
    try:
        a,s,d=x.split("$")[1:]; h=hashlib.pbkdf2_hmac("sha256",p.encode(),s.encode(),int(a)).hex()
        return secrets.compare_digest(h,d)
    except: return False
def rup(x): return "Rp {:,.0f}".format(float(x or 0)).replace(",","." )
def ts(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def init():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE,name TEXT,role TEXT,password_hash TEXT,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,barcode TEXT UNIQUE,name TEXT,category TEXT DEFAULT '',cost_price REAL DEFAULT 0,selling_price REAL DEFAULT 0,stock REAL DEFAULT 0,min_stock REAL DEFAULT 0,unit TEXT DEFAULT 'pcs',active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,phone TEXT,address TEXT,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,phone TEXT,address TEXT,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_no TEXT UNIQUE,created_at TEXT,user_id INTEGER,customer_id INTEGER,subtotal REAL,discount REAL DEFAULT 0,total REAL,paid REAL,change REAL,payment_method TEXT);
        CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY AUTOINCREMENT,sale_id INTEGER,product_id INTEGER,quantity REAL,unit_price REAL,discount REAL DEFAULT 0,line_total REAL);
        CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_no TEXT UNIQUE,created_at TEXT,supplier_id INTEGER,total REAL,paid REAL,notes TEXT);
        CREATE TABLE IF NOT EXISTS purchase_items(id INTEGER PRIMARY KEY AUTOINCREMENT,purchase_id INTEGER,product_id INTEGER,quantity REAL,unit_cost REAL,line_total REAL);
        CREATE TABLE IF NOT EXISTS stock_movements(id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER,movement_type TEXT,quantity REAL,reference TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        """)
        if not c.execute("select 1 from users limit 1").fetchone():
            c.execute("insert into users(username,name,role,password_hash) values(?,?,?,?)",("admin","Administrator","ADMIN",pw_hash("admin112233")))
        for k,v in {"store_name":"WPOS PRO 2","store_address":"","store_phone":"","receipt_footer":"Terima kasih","tax_percent":"0"}.items():
            c.execute("insert or ignore into settings(key,value) values(?,?)",(k,v))
def setting(k):
    with db() as c:
        r=c.execute("select value from settings where key=?",(k,)).fetchone()
        return r["value"] if r else ""
def backup():
    folder=os.path.join(ROOT,"backups");os.makedirs(folder,exist_ok=True)
    out=os.path.join(folder,"wpos_"+datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+".db");shutil.copy2(DB,out);return out

class Login(tk.Tk):
    def __init__(self):
        super().__init__();self.title(APP);self.geometry("470x450");self.configure(bg="#0c1730")
        f=tk.Frame(self,bg="#172442",padx=35,pady=28);f.place(relx=.5,rely=.5,anchor="center",relwidth=.85,relheight=.85)
        tk.Label(f,text=APP,font=("Segoe UI",24,"bold"),fg="white",bg="#172442").pack(pady=8)
        tk.Label(f,text="Offline Point of Sale",fg="#a9bad5",bg="#172442").pack(pady=(0,25))
        tk.Label(f,text="Username",fg="white",bg="#172442").pack(anchor="w");self.u=ttk.Entry(f);self.u.pack(fill="x",ipady=7,pady=(3,12))
        tk.Label(f,text="Password",fg="white",bg="#172442").pack(anchor="w");self.p=ttk.Entry(f,show="•");self.p.pack(fill="x",ipady=7,pady=(3,18))
        ttk.Button(f,text="MASUK",command=self.login).pack(fill="x",ipady=7);self.p.bind("<Return>",lambda e:self.login())
    def login(self):
        with db() as c:r=c.execute("select * from users where username=? and active=1",(self.u.get().strip(),)).fetchone()
        if not r or not pw_ok(self.p.get(),r["password_hash"]): messagebox.showerror("Login","Username atau password salah.");return
        self.withdraw();App(self,dict(r))

class App(tk.Toplevel):
    def __init__(self,root,user):
        super().__init__(root);self.root=root;self.user=user;self.title(APP+" - "+user["role"]);self.geometry("1280x780");self.minsize(1080,650)
        self.protocol("WM_DELETE_WINDOW",root.destroy);self.nb=ttk.Notebook(self);self.nb.pack(fill="both",expand=True,padx=10,pady=10)
        self.build()
    def tab(self,n):
        f=tk.Frame(self.nb,bg="#f3f6fb");self.nb.add(f,text=n);return f
    def tree(self,f,cols,widths):
        t=ttk.Treeview(f,columns=cols,show="headings")
        for a,w in zip(cols,widths):t.heading(a,text=a.replace("_"," ").title());t.column(a,width=w)
        t.pack(fill="both",expand=True,padx=12,pady=12);return t
    def build(self):
        self.dashboard()
        self.cashier()
        if self.user["role"]=="ADMIN":
            self.products();self.stock();self.purchase();self.master("Pelanggan","customers");self.master("Supplier","suppliers");self.users();self.settings()
        self.reports()
    def dashboard(self):
        f=self.tab("Dashboard");top=tk.Frame(f,bg="#f3f6fb");top.pack(fill="x",padx=20,pady=20)
        with db() as c:
            a=c.execute("select count(*) n from products").fetchone()["n"];b=c.execute("select coalesce(sum(stock),0) n from products").fetchone()["n"]
            d=c.execute("select coalesce(sum(total),0) n from sales where date(created_at)=date('now','localtime')").fetchone()["n"]
            e=c.execute("select count(*) n from sales where date(created_at)=date('now','localtime')").fetchone()["n"]
        for n,v in [("Produk",a),("Stok",b),("Penjualan Hari Ini",rup(d)),("Transaksi Hari Ini",e)]:
            x=tk.Frame(top,bg="white",padx=18,pady=15);x.pack(side="left",fill="x",expand=True,padx=5)
            tk.Label(x,text=n,bg="white",fg="#66758b").pack(anchor="w");tk.Label(x,text=v,bg="white",fg="#14213d",font=("Segoe UI",19,"bold")).pack(anchor="w")
        tk.Label(f,text="WPOS PRO 2",bg="#f3f6fb",fg="#14213d",font=("Segoe UI",22,"bold")).pack(anchor="w",padx=25,pady=10)
        tk.Label(f,text="Tahap 1–4 terintegrasi: login, dashboard, kasir, stok, pembelian, master data, laporan, pengaturan, backup dan printer.",bg="#f3f6fb",fg="#65748b").pack(anchor="w",padx=25)
    def cashier(self):
        f=self.tab("Kasir");left=tk.Frame(f,bg="white");left.pack(side="left",fill="both",expand=True,padx=(10,5),pady=10);right=tk.Frame(f,bg="white",width=370);right.pack(side="right",fill="y",padx=(5,10),pady=10);right.pack_propagate(False)
        q=ttk.Entry(left);q.pack(fill="x",padx=12,pady=12,ipady=6);t=self.tree(left,["barcode","name","price","stock"],[130,300,120,80]);cart=[]
        ct=self.tree(right,["product","qty","total"],[170,55,120]);total=tk.StringVar(value="Rp 0");tk.Label(right,textvariable=total,font=("Segoe UI",20,"bold"),bg="white").pack(anchor="e",padx=12,pady=8)
        def load(*_):
            t.delete(*t.get_children());s="%"+q.get()+"%"
            with db() as c:rs=c.execute("select barcode,name,selling_price,stock from products where active=1 and (barcode like ? or name like ?) order by name",(s,s)).fetchall()
            for r in rs:t.insert("","end",values=(r["barcode"],r["name"],rup(r["selling_price"]),r["stock"]))
        def add():
            i=t.focus()
            if not i:return
            bar=t.item(i,"values")[0]
            with db() as c:r=c.execute("select * from products where barcode=?",(bar,)).fetchone()
            for x in cart:
                if x["id"]==r["id"]:x["qty"]+=1;break
            else:cart.append({"id":r["id"],"name":r["name"],"price":float(r["selling_price"]),"qty":1})
            refresh()
        def refresh():
            ct.delete(*ct.get_children());z=sum(x["price"]*x["qty"] for x in cart);total.set(rup(z))
            for x in cart:ct.insert("","end",values=(x["name"],x["qty"],rup(x["price"]*x["qty"])))
        def pay():
            if not cart:return
            z=sum(x["price"]*x["qty"] for x in cart);p=simpledialog.askfloat("Pembayaran","Total "+rup(z)+"\nUang dibayar:",parent=self,minvalue=z)
            if p is None:return
            inv="INV-"+datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
            try:
                with db() as c:
                    c.execute("insert into sales(invoice_no,created_at,user_id,subtotal,total,paid,change,payment_method) values(?,?,?,?,?,?,?,?)",(inv,ts(),self.user["id"],z,z,p,p-z,"CASH"));sid=c.execute("select last_insert_rowid()").fetchone()[0]
                    for x in cart:
                        s=c.execute("select stock from products where id=?",(x["id"],)).fetchone()["stock"]
                        if s<x["qty"]:raise ValueError("Stok "+x["name"]+" tidak cukup")
                        c.execute("insert into sale_items(sale_id,product_id,quantity,unit_price,line_total) values(?,?,?,?,?)",(sid,x["id"],x["qty"],x["price"],x["qty"]*x["price"]))
                        c.execute("update products set stock=stock-? where id=?",(x["qty"],x["id"]))
                        c.execute("insert into stock_movements(product_id,movement_type,quantity,reference,created_at) values(?,?,?,?,?)",(x["id"],"SALE",-x["qty"],inv,ts()))
                self.print_receipt(inv,cart,z,p,p-z);cart.clear();refresh();load()
            except Exception as e:messagebox.showerror("Kasir",str(e))
        q.bind("<KeyRelease>",load);ttk.Button(left,text="Tambah",command=add).pack(anchor="e",padx=12,pady=5);ttk.Button(right,text="CHECKOUT & CETAK",command=pay).pack(fill="x",padx=12,pady=10,ipady=8);load()
    def print_receipt(self,inv,cart,total,paid,change):
        s=setting("store_name")+"\\n"+setting("store_address")+"\\n"+"-"*40+"\\n"+inv+"  "+ts()+"\\n"
        for x in cart:s+=x["name"][:22]+" x"+str(x["qty"])+" "+rup(x["price"]*x["qty"])+"\\n"
        s+="-"*40+"\\nTOTAL "+rup(total)+"\\nBAYAR "+rup(paid)+"\\nKEMBALI "+rup(change)+"\\n"+setting("receipt_footer")
        p=os.path.join(tempfile.gettempdir(),inv+".txt");open(p,"w",encoding="utf8").write(s)
        try:
            if sys.platform.startswith("win"):os.startfile(p,"print")
        except:pass
        messagebox.showinfo("Transaksi",s)
    def products(self):
        f=self.tab("Produk");bar=tk.Frame(f,bg="#f3f6fb");bar.pack(fill="x",padx=12,pady=8);t=self.tree(f,["id","barcode","name","category","cost","price","stock","min","unit"],[45,110,240,110,100,100,80,70,60])
        def load():
            t.delete(*t.get_children())
            with db() as c:rs=c.execute("select id,barcode,name,category,cost_price,selling_price,stock,min_stock,unit from products order by name").fetchall()
            for r in rs:t.insert("","end",values=tuple(r))
        def form(vals=None):
            d=tk.Toplevel(self);d.title("Produk");d.geometry("400x500");es={}
            for k,l in [("barcode","Barcode"),("name","Nama"),("category","Kategori"),("cost_price","Harga Beli"),("selling_price","Harga Jual"),("stock","Stok"),("min_stock","Minimum"),("unit","Satuan")]:
                tk.Label(d,text=l).pack(anchor="w",padx=20);e=ttk.Entry(d);e.pack(fill="x",padx=20,pady=4);es[k]=e
            if vals:
                for k,v in zip(es,vals[1:]):es[k].insert(0,v or "")
            def save():
                v=[es[k].get().strip() for k in es]
                try:
                    with db() as c:
                        if vals:c.execute("update products set barcode=?,name=?,category=?,cost_price=?,selling_price=?,stock=?,min_stock=?,unit=? where id=?",(*v[:3],float(v[3] or 0),float(v[4] or 0),float(v[5] or 0),float(v[6] or 0),v[7] or "pcs",vals[0]))
                        else:c.execute("insert into products(barcode,name,category,cost_price,selling_price,stock,min_stock,unit) values(?,?,?,?,?,?,?,?)",(v[0] or None,v[1],v[2],float(v[3] or 0),float(v[4] or 0),float(v[5] or 0),float(v[6] or 0),v[7] or "pcs"))
                    d.destroy();load()
                except Exception as e:messagebox.showerror("Produk",str(e))
            ttk.Button(d,text="Simpan",command=save).pack(pady=15)
        ttk.Button(bar,text="Tambah",command=form).pack(side="left");ttk.Button(bar,text="Edit",command=lambda:form(t.item(t.focus(),"values") if t.focus() else None)).pack(side="left",padx=5);load()
    def stock(self):
        f=self.tab("Stok");t=self.tree(f,["barcode","name","stock","minimum","status"],[140,330,120,120,120])
        def load():
            t.delete(*t.get_children())
            with db() as c:rs=c.execute("select barcode,name,stock,min_stock from products order by name").fetchall()
            for r in rs:t.insert("","end",values=(r["barcode"],r["name"],r["stock"],r["min_stock"],"MENIPIS" if r["stock"]<=r["min_stock"] else "Aman"))
        def adj():
            i=t.focus()
            if not i:return
            q=simpledialog.askfloat("Stok","Jumlah penyesuaian (+/-):",parent=self)
            if q is None:return
            with db() as c:
                r=c.execute("select id from products where barcode=?",(t.item(i,"values")[0],)).fetchone()
                c.execute("update products set stock=stock+? where id=?",(q,r["id"]));c.execute("insert into stock_movements(product_id,movement_type,quantity,reference,created_at) values(?,?,?,?,?)",(r["id"],"ADJUST",q,"MANUAL",ts()))
            load()
        ttk.Button(f,text="Penyesuaian Stok",command=adj).pack(anchor="w",padx=12,pady=8);load()
    def purchase(self):
        f=self.tab("Pembelian");tk.Label(f,text="Pembelian / Stok Masuk",font=("Segoe UI",18,"bold"),bg="#f3f6fb").pack(anchor="w",padx=20,pady=20)
        tk.Label(f,text="Gunakan menu Produk untuk menambah barang; stok masuk dapat dicatat melalui penyesuaian stok. Struktur pembelian sudah tersedia untuk pengembangan transaksi pembelian penuh.",bg="#f3f6fb",fg="#64748b",wraplength=900).pack(anchor="w",padx=20)
    def master(self,title,table):
        f=self.tab(title);t=self.tree(f,["id","name","phone","address"],[60,280,180,450])
        def load():
            t.delete(*t.get_children())
            with db() as c:rs=c.execute("select id,name,phone,address from "+table+" order by name").fetchall()
            for r in rs:t.insert("","end",values=tuple(r))
        def form(vals=None):
            d=tk.Toplevel(self);d.title(title);d.geometry("420x320");es=[]
            for l in ["Nama","Telepon","Alamat"]:
                tk.Label(d,text=l).pack(anchor="w",padx=20);e=ttk.Entry(d);e.pack(fill="x",padx=20,pady=5);es.append(e)
            if vals:
                for e,v in zip(es,vals[1:]):e.insert(0,v or "")
            def save():
                with db() as c:
                    if vals:c.execute("update "+table+" set name=?,phone=?,address=? where id=?",(es[0].get(),es[1].get(),es[2].get(),vals[0]))
                    else:c.execute("insert into "+table+"(name,phone,address) values(?,?,?)",[e.get() for e in es])
                d.destroy();load()
            ttk.Button(d,text="Simpan",command=save).pack(pady=15)
        ttk.Button(f,text="Tambah",command=form).pack(anchor="w",padx=12,pady=8);ttk.Button(f,text="Edit",command=lambda:form(t.item(t.focus(),"values") if t.focus() else None)).pack(anchor="w",padx=12);load()
    def users(self):
        f=self.tab("Pengguna");t=self.tree(f,["id","username","name","role","status"],[60,180,240,100,100])
        def load():
            t.delete(*t.get_children())
            with db() as c:rs=c.execute("select id,username,name,role,active from users").fetchall()
            for r in rs:t.insert("","end",values=(r["id"],r["username"],r["name"],r["role"],"Aktif" if r["active"] else "Nonaktif"))
        def reset():
            i=t.focus()
            if not i:return
            u=t.item(i,"values")[1];p=simpledialog.askstring("Reset Password","Password baru untuk "+u,show="•",parent=self)
            if not p:return
            if len(p)<6:return messagebox.showwarning("Password","Minimal 6 karakter")
            b=backup()
            with db() as c:c.execute("update users set password_hash=? where username=?",(pw_hash(p),u))
            messagebox.showinfo("Reset","Password diubah. Backup: "+b)
        ttk.Button(f,text="Reset Password",command=reset).pack(anchor="w",padx=12,pady=8);load()
    def reports(self):
        f=self.tab("Laporan");bar=tk.Frame(f,bg="#f3f6fb");bar.pack(fill="x",padx=12,pady=8);t=self.tree(f,["invoice","tanggal","total","bayar","kembalian"],[200,190,160,160,160])
        def load():
            t.delete(*t.get_children())
            with db() as c:rs=c.execute("select invoice_no,created_at,total,paid,change from sales order by id desc limit 1000").fetchall()
            for r in rs:t.insert("","end",values=(r["invoice_no"],r["created_at"],rup(r["total"]),rup(r["paid"]),rup(r["change"])))
        def export():
            p=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV","*.csv")])
            if not p:return
            with open(p,"w",newline="",encoding="utf8-sig") as x:
                w=csv.writer(x);w.writerow(["Invoice","Tanggal","Total","Bayar","Kembalian"])
                for i in t.get_children():w.writerow(t.item(i,"values"))
            messagebox.showinfo("Laporan","Tersimpan")
        ttk.Button(bar,text="Export CSV",command=export).pack(side="left");load()
    def settings(self):
        f=self.tab("Pengaturan");box=tk.Frame(f,bg="white",padx=25,pady=25);box.pack(fill="x",padx=20,pady=20);es={}
        for k,l in [("store_name","Nama Toko"),("store_address","Alamat"),("store_phone","Telepon"),("receipt_footer","Footer Struk"),("tax_percent","Pajak %")]:
            tk.Label(box,text=l,bg="white").pack(anchor="w");e=ttk.Entry(box);e.pack(fill="x",pady=4);e.insert(0,setting(k));es[k]=e
        def save():
            with db() as c:
                for k,e in es.items():c.execute("insert or replace into settings(key,value) values(?,?)",(k,e.get()))
            messagebox.showinfo("Pengaturan","Tersimpan")
        ttk.Button(box,text="Simpan",command=save).pack(anchor="w",pady=8);ttk.Button(box,text="Backup Database",command=lambda:messagebox.showinfo("Backup",backup())).pack(anchor="w")

if __name__=="__main__":
    init();Login().mainloop()
