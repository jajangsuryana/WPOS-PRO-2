import os,sys,sqlite3,hashlib,secrets,shutil,datetime,csv,tempfile,tkinter as tk
from tkinter import ttk,messagebox,simpledialog,filedialog
APP="WPOS PRO 2"; ROOT=os.path.dirname(os.path.abspath(sys.executable if getattr(sys,"frozen",False) else __file__)); DB=os.path.join(ROOT,"wpos.db")
def con():
    c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def now(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def rup(x):
    try:x=float(x or 0)
    except:x=0
    return "Rp {:,.0f}".format(x).replace(",",".")
def ph(p):
    s=secrets.token_hex(16);return "pbkdf2_sha256$210000$"+s+"$"+hashlib.pbkdf2_hmac("sha256",p.encode(),s.encode(),210000).hex()
def pv(p,h):
    try:a,n,s,d=h.split("$",3);return a=="pbkdf2_sha256" and secrets.compare_digest(hashlib.pbkdf2_hmac("sha256",p.encode(),s.encode(),int(n)).hex(),d)
    except:return False
def init():
    with con() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,name TEXT,role TEXT DEFAULT 'KASIR',password_hash TEXT,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,barcode TEXT UNIQUE,name TEXT,category TEXT DEFAULT '',cost_price REAL DEFAULT 0,selling_price REAL DEFAULT 0,stock REAL DEFAULT 0,min_stock REAL DEFAULT 0,unit TEXT DEFAULT 'pcs',active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY,name TEXT,phone TEXT DEFAULT '',address TEXT DEFAULT '',active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY,name TEXT,phone TEXT DEFAULT '',address TEXT DEFAULT '',active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY,invoice_no TEXT UNIQUE,created_at TEXT,user_id INTEGER,customer_id INTEGER,subtotal REAL DEFAULT 0,discount REAL DEFAULT 0,total REAL DEFAULT 0,paid REAL DEFAULT 0,change REAL DEFAULT 0,payment_method TEXT DEFAULT 'CASH');
        CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY,sale_id INTEGER,product_id INTEGER,quantity REAL,unit_price REAL,line_total REAL);
        CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY,invoice_no TEXT UNIQUE,created_at TEXT,user_id INTEGER,supplier_id INTEGER,total REAL DEFAULT 0,paid REAL DEFAULT 0,notes TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS purchase_items(id INTEGER PRIMARY KEY,purchase_id INTEGER,product_id INTEGER,quantity REAL,unit_cost REAL,line_total REAL);
        CREATE TABLE IF NOT EXISTS stock_movements(id INTEGER PRIMARY KEY,product_id INTEGER,movement_type TEXT,quantity REAL,reference TEXT,created_at TEXT,user_id INTEGER);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        """)
        def col(t,n,d):
            if n not in [x["name"] for x in c.execute("pragma table_info("+t+")")]:c.execute("alter table "+t+" add column "+n+" "+d)
        for t,items in {"users":[("name","TEXT"),("role","TEXT DEFAULT 'KASIR'"),("password_hash","TEXT"),("active","INTEGER DEFAULT 1")],
                        "products":[("barcode","TEXT"),("category","TEXT DEFAULT ''"),("cost_price","REAL DEFAULT 0"),("selling_price","REAL DEFAULT 0"),("stock","REAL DEFAULT 0"),("min_stock","REAL DEFAULT 0"),("unit","TEXT DEFAULT 'pcs'"),("active","INTEGER DEFAULT 1")],
                        "customers":[("phone","TEXT DEFAULT ''"),("address","TEXT DEFAULT ''"),("active","INTEGER DEFAULT 1")],
                        "suppliers":[("phone","TEXT DEFAULT ''"),("address","TEXT DEFAULT ''"),("active","INTEGER DEFAULT 1")],
                        "sales":[("customer_id","INTEGER"),("subtotal","REAL DEFAULT 0"),("discount","REAL DEFAULT 0"),("total","REAL DEFAULT 0"),("paid","REAL DEFAULT 0"),("change","REAL DEFAULT 0"),("payment_method","TEXT DEFAULT 'CASH'")]}.items():
            for n,d in items:col(t,n,d)
        if not c.execute("select 1 from users limit 1").fetchone():c.execute("insert into users(username,name,role,password_hash) values(?,?,?,?)",("admin","Administrator","ADMIN",ph("admin112233")))
        for k,v in {"store_name":"WPOS PRO 2","store_address":"","store_phone":"","receipt_footer":"Terima kasih","printer_name":"","receipt_width":"58mm"}.items():c.execute("insert or ignore into settings values(?,?)",(k,v))
def get(k):
    with con() as c:r=c.execute("select value from settings where key=?",(k,)).fetchone();return r["value"] if r else ""
def setv(k,v):
    with con() as c:c.execute("insert or replace into settings values(?,?)",(k,str(v)))
def backup():
    os.makedirs(os.path.join(ROOT,"backups"),exist_ok=True);p=os.path.join(ROOT,"backups","wpos_"+datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+".db")
    a=sqlite3.connect(DB);b=sqlite3.connect(p);a.backup(b);b.close();a.close();return p

class Login(tk.Tk):
    def __init__(self):
        super().__init__();self.title(APP+" - Login");self.geometry("500x520");self.configure(bg="#0b1220")
        f=tk.Frame(self,bg="#111b2e");f.place(relx=.5,rely=.5,anchor="center",relwidth=.82,relheight=.82)
        tk.Label(f,text="WPOS PRO 2",font=("Segoe UI",27,"bold"),fg="white",bg="#111b2e").pack(pady=(45,5));tk.Label(f,text="OFFLINE POINT OF SALE",fg="#60a5fa",bg="#111b2e").pack(pady=(0,30))
        tk.Label(f,text="Username",fg="white",bg="#111b2e").pack(anchor="w",padx=35);self.u=ttk.Entry(f);self.u.pack(fill="x",padx=35,pady=(5,15),ipady=7)
        tk.Label(f,text="Password",fg="white",bg="#111b2e").pack(anchor="w",padx=35);self.p=ttk.Entry(f,show="•");self.p.pack(fill="x",padx=35,pady=(5,18),ipady=7)
        ttk.Button(f,text="MASUK",command=self.login).pack(fill="x",padx=35,ipady=8);self.p.bind("<Return>",lambda e:self.login());self.u.focus()
    def login(self):
        with con() as c:r=c.execute("select * from users where username=? and active=1",(self.u.get().strip(),)).fetchone()
        if not r or not pv(self.p.get(),r["password_hash"]):messagebox.showerror("Login","Username atau password salah.",parent=self);return
        self.withdraw();Main(self,dict(r))

class Main(tk.Toplevel):
    def __init__(self,root,user):
        super().__init__(root);self.root=root;self.user=user;self.cart=[];self.page="Dashboard";self.title(APP+" - "+user["role"]);self.geometry("1380x820");self.minsize(1100,680);self.configure(bg="#eef2f7")
        self.protocol("WM_DELETE_WINDOW",root.destroy);self.bind_all("<F2>",lambda e:self.show("Kasir"));self.bind_all("<F4>",lambda e:self.show("Produk"));self.bind_all("<F5>",lambda e:self.show(self.page))
        self.side=tk.Frame(self,bg="#0f172a",width=230);self.side.pack(side="left",fill="y");self.side.pack_propagate(False);self.body=tk.Frame(self,bg="#eef2f7");self.body.pack(side="right",fill="both",expand=True)
        tk.Label(self.side,text="WPOS",font=("Segoe UI",23,"bold"),fg="white",bg="#0f172a").pack(anchor="w",padx=20,pady=(25,0));tk.Label(self.side,text="PRO 2  •  OFFLINE",fg="#60a5fa",bg="#0f172a").pack(anchor="w",padx=20,pady=(0,20))
        names=["Dashboard","Kasir"]+([] if user["role"]!="ADMIN" else ["Produk","Stok","Pembelian","Pelanggan","Supplier","Pengguna"])+["Laporan"]+([] if user["role"]!="ADMIN" else ["Printer Center","Pengaturan"])
        for n in names:
            tk.Button(self.side,text="  "+n,anchor="w",command=lambda x=n:self.show(x),bg="#0f172a",fg="#cbd5e1",activebackground="#1e293b",activeforeground="white",bd=0,font=("Segoe UI",10,"bold")).pack(fill="x",padx=10,pady=2,ipady=8)
        tk.Frame(self.side,bg="#111827").pack(fill="both",expand=True)
        tk.Label(self.side,text=user["name"],fg="white",bg="#111827",font=("Segoe UI",9,"bold")).pack(fill="x",padx=15,pady=(10,0));tk.Label(self.side,text=user["role"],fg="#60a5fa",bg="#111827").pack(fill="x",padx=15,pady=(0,8));ttk.Button(self.side,text="KELUAR",command=self.logout).pack(fill="x",padx=12,pady=12)
        self.show("Dashboard")
    def logout(self):self.destroy();self.root.deiconify()
    def clear(self):
        for w in self.body.winfo_children():w.destroy()
    def head(self,title,sub=""):
        self.clear();tk.Label(self.body,text=title,font=("Segoe UI",24,"bold"),fg="#0f172a",bg="#eef2f7").pack(anchor="w",padx=28,pady=(22,2));tk.Label(self.body,text=sub,fg="#64748b",bg="#eef2f7").pack(anchor="w",padx=28,pady=(0,12))
    def show(self,n):
        self.page=n;f=getattr(self,"p_"+n.lower().replace(" ","_"),None)
        if f:f()
        else:self.head(n)
    def tree(self,parent,cols):
        t=ttk.Treeview(parent,columns=[x[0] for x in cols],show="headings")
        for n,w in cols:t.heading(n,text=n);t.column(n,width=w)
        s=ttk.Scrollbar(parent,command=t.yview);t.configure(yscrollcommand=s.set);t.pack(side="left",fill="both",expand=True,padx=(22,0),pady=8);s.pack(side="right",fill="y",padx=(0,22),pady=8);return t
    def p_dashboard(self):
        self.head("Dashboard","Ringkasan toko • realtime")
        box=tk.Frame(self.body,bg="#eef2f7");box.pack(fill="x",padx=22,pady=8)
        with con() as c:
            vals=[c.execute("select count(*) n from products where active=1").fetchone()["n"],c.execute("select coalesce(sum(stock),0) n from products where active=1").fetchone()["n"],c.execute("select coalesce(sum(total),0) n from sales where date(created_at)=date('now','localtime')").fetchone()["n"],c.execute("select count(*) n from sales where date(created_at)=date('now','localtime')").fetchone()["n"],c.execute("select count(*) n from products where active=1 and stock<=min_stock").fetchone()["n"]]
        for lab,val in zip(["Produk","Total Stok","Omzet Hari Ini","Transaksi Hari Ini","Stok Menipis"],vals):
            f=tk.Frame(box,bg="white",highlightthickness=1,highlightbackground="#e2e8f0");f.pack(side="left",fill="both",expand=True,padx=5);tk.Label(f,text=lab.upper(),fg="#64748b",bg="white",font=("Segoe UI",8,"bold")).pack(anchor="w",padx=15,pady=(15,3));tk.Label(f,text=rup(val) if lab=="Omzet Hari Ini" else val,font=("Segoe UI",18,"bold"),fg="#0f172a",bg="white").pack(anchor="w",padx=15,pady=(0,15))
        pane=tk.Frame(self.body,bg="white");pane.pack(fill="both",expand=True,padx=28,pady=15);tk.Label(pane,text="Transaksi Terakhir",font=("Segoe UI",13,"bold"),bg="white").pack(anchor="w",padx=20,pady=12)
        t=self.tree(pane,[("Invoice",210),("Tanggal",180),("Total",150),("Metode",120)])
        with con() as c:rows=c.execute("select invoice_no,created_at,total,payment_method from sales order by id desc limit 15").fetchall()
        for r in rows:t.insert("","end",values=(r["invoice_no"],r["created_at"],rup(r["total"]),r["payment_method"]))
    def p_kasir(self):
        self.head("Kasir","F2 • cari produk • double click untuk menambah")
        main=tk.Frame(self.body,bg="#eef2f7");main.pack(fill="both",expand=True,padx=22)
        l=tk.Frame(main,bg="white");l.pack(side="left",fill="both",expand=True,padx=(0,8));r=tk.Frame(main,bg="white",width=390);r.pack(side="right",fill="y");r.pack_propagate(False)
        q=tk.StringVar();ttk.Entry(l,textvariable=q).pack(fill="x",padx=15,pady=12,ipady=7);t=self.tree(l,[("Barcode",130),("Produk",300),("Harga",130),("Stok",90)])
        def load(*_):
            t.delete(*t.get_children());s="%"+q.get()+"%"
            with con() as c:rs=c.execute("select id,barcode,name,selling_price,stock from products where active=1 and (barcode like ? or name like ?) order by name",(s,s)).fetchall()
            for x in rs:t.insert("","end",iid=str(x["id"]),values=(x["barcode"] or "",x["name"],rup(x["selling_price"]),x["stock"]))
        def add(e=None):
            i=t.focus()
            if not i:return
            with con() as c:x=c.execute("select * from products where id=?",(i,)).fetchone()
            z=next((z for z in self.cart if z["id"]==x["id"]),None)
            if z:z["qty"]+=1
            else:self.cart.append({"id":x["id"],"name":x["name"],"price":float(x["selling_price"]),"qty":1})
            refresh()
        t.bind("<Double-1>",add);q.trace_add("write",load);ttk.Button(l,text="TAMBAH",command=add).pack(anchor="e",padx=15,pady=7)
        tk.Label(r,text="KERANJANG",font=("Segoe UI",13,"bold"),bg="white").pack(anchor="w",padx=16,pady=14);ct=self.tree(r,[("Produk",190),("Qty",55),("Total",120)])
        total=tk.StringVar(value="Rp 0");disc=tk.DoubleVar(value=0);paid=tk.DoubleVar(value=0);meth=tk.StringVar(value="CASH");sm=tk.Frame(r,bg="white");sm.pack(fill="x",padx=16);sub=tk.StringVar(value="Rp 0");change=tk.StringVar(value="Kembalian Rp 0")
        for row,label,var in [(0,"Subtotal",sub),(2,"TOTAL",total),(5,"",change)]:
            tk.Label(sm,text=label,font=("Segoe UI",12,"bold") if row==2 else ("Segoe UI",9),bg="white").grid(row=row,column=0,sticky="w",pady=5);tk.Label(sm,textvariable=var,font=("Segoe UI",15,"bold") if row==2 else ("Segoe UI",9,"bold"),bg="white",fg="#2563eb" if row==2 else "#16a34a").grid(row=row,column=1,sticky="e")
        tk.Label(sm,text="Diskon",bg="white").grid(row=1,column=0,sticky="w");ttk.Entry(sm,textvariable=disc,width=14).grid(row=1,column=1,sticky="e");tk.Label(sm,text="Metode",bg="white").grid(row=3,column=0,sticky="w");ttk.Combobox(sm,textvariable=meth,values=["CASH","TRANSFER","QRIS","DEBIT"],state="readonly",width=12).grid(row=3,column=1,sticky="e");tk.Label(sm,text="Bayar",bg="white").grid(row=4,column=0,sticky="w");ttk.Entry(sm,textvariable=paid,width=14).grid(row=4,column=1,sticky="e")
        def refresh():
            ct.delete(*ct.get_children());a=sum(x["price"]*x["qty"] for x in self.cart);b=max(0,a-float(disc.get() or 0));sub.set(rup(a));total.set(rup(b));change.set("Kembalian "+rup(max(0,float(paid.get() or 0)-b)))
            for x in self.cart:ct.insert("","end",values=(x["name"],x["qty"],rup(x["price"]*x["qty"])))
        disc.trace_add("write",lambda *_:refresh());paid.trace_add("write",lambda *_:refresh())
        def pay():
            if not self.cart:return messagebox.showwarning("Kasir","Keranjang kosong.",parent=self)
            a=sum(x["price"]*x["qty"] for x in self.cart);d=float(disc.get() or 0);tot=max(0,a-d);p=float(paid.get() or 0)
            if meth.get()=="CASH" and p<tot:return messagebox.showwarning("Kasir","Uang kurang.",parent=self)
            inv="INV-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            try:
                with con() as c:
                    for x in self.cart:
                        s=c.execute("select stock from products where id=?",(x["id"],)).fetchone()
                        if not s or s["stock"]<x["qty"]:raise ValueError("Stok tidak cukup: "+x["name"])
                    c.execute("insert into sales(invoice_no,created_at,user_id,subtotal,discount,total,paid,change,payment_method) values(?,?,?,?,?,?,?,?,?)",(inv,now(),self.user["id"],a,d,tot,p,max(0,p-tot),meth.get()));sid=c.execute("select last_insert_rowid()").fetchone()[0]
                    for x in self.cart:
                        c.execute("insert into sale_items(sale_id,product_id,quantity,unit_price,line_total) values(?,?,?,?,?)",(sid,x["id"],x["qty"],x["price"],x["qty"]*x["price"]));c.execute("update products set stock=stock-? where id=?",(x["qty"],x["id"]));c.execute("insert into stock_movements(product_id,movement_type,quantity,reference,created_at,user_id) values(?,?,?,?,?,?)",(x["id"],"SALE",-x["qty"],inv,now(),self.user["id"]))
                txt=get("store_name")+"\n"+inv+"\n"+"-"*35+"\n"+"".join(x["name"]+" x"+str(x["qty"])+" "+rup(x["price"]*x["qty"])+"\n" for x in self.cart)+"-"*35+"\nTOTAL "+rup(tot)+"\nBAYAR "+rup(p)+"\nKEMBALI "+rup(max(0,p-tot))+"\n"+get("receipt_footer")
                path=os.path.join(tempfile.gettempdir(),"wpos_"+inv+".txt");open(path,"w",encoding="utf8").write(txt)
                if sys.platform.startswith("win") and get("printer_name"):
                    try:os.startfile(path,"print")
                    except:pass
                messagebox.showinfo("Transaksi Berhasil",txt,parent=self);self.cart.clear();refresh();load()
            except Exception as e:messagebox.showerror("Kasir",str(e),parent=self)
        ttk.Button(r,text="CHECKOUT • CETAK",command=pay).pack(fill="x",padx=16,pady=18,ipady=8);load();refresh()
    def p_produk(self):
        self.head("Produk","Master barang dan harga")
        bar=tk.Frame(self.body,bg="#eef2f7");bar.pack(fill="x",padx=22);search=tk.StringVar();ttk.Entry(bar,textvariable=search,width=32).pack(side="left",ipady=6)
        t=self.tree(self.body,[("ID",50),("Barcode",130),("Nama",270),("Kategori",130),("Beli",110),("Jual",110),("Stok",80),("Min",70),("Satuan",70)])
        def load(*_):
            t.delete(*t.get_children());s="%"+search.get()+"%"
            with con() as c:rs=c.execute("select id,barcode,name,category,cost_price,selling_price,stock,min_stock,unit from products where active=1 and (name like ? or barcode like ?) order by name",(s,s)).fetchall()
            for x in rs:t.insert("","end",values=tuple(x))
        def form(row=None):
            d=tk.Toplevel(self);d.title("Produk");d.geometry("440x540");ks=["barcode","name","category","cost_price","selling_price","stock","min_stock","unit"];es={}
            for k in ks:tk.Label(d,text=k.replace("_"," ").title()).pack(anchor="w",padx=20,pady=(7,0));e=ttk.Entry(d);e.pack(fill="x",padx=20);es[k]=e
            if row:
                for k,v in zip(ks,row[1:]):es[k].insert(0,v or "")
            def save():
                try:
                    v={k:es[k].get().strip() for k in ks}
                    for k in ["cost_price","selling_price","stock","min_stock"]:v[k]=float(v[k] or 0)
                    with con() as c:
                        if row:c.execute("update products set barcode=?,name=?,category=?,cost_price=?,selling_price=?,stock=?,min_stock=?,unit=? where id=?",(v["barcode"] or None,v["name"],v["category"],v["cost_price"],v["selling_price"],v["stock"],v["min_stock"],v["unit"] or "pcs",row[0]))
                        else:c.execute("insert into products(barcode,name,category,cost_price,selling_price,stock,min_stock,unit) values(?,?,?,?,?,?,?,?)",(v["barcode"] or None,v["name"],v["category"],v["cost_price"],v["selling_price"],v["stock"],v["min_stock"],v["unit"] or "pcs"))
                    d.destroy();load()
                except Exception as e:messagebox.showerror("Produk",str(e),parent=d)
            ttk.Button(d,text="SIMPAN",command=save).pack(pady=15)
        ttk.Button(bar,text="＋ TAMBAH",command=form).pack(side="left",padx=8);ttk.Button(bar,text="EDIT",command=lambda:form(t.item(t.focus(),"values") if t.focus() else None)).pack(side="left");search.trace_add("write",load);load()
    def p_stok(self):
        self.head("Stok","Kontrol stok dan penyesuaian")
        bar=tk.Frame(self.body,bg="#eef2f7");bar.pack(fill="x",padx=22);t=self.tree(self.body,[("Barcode",130),("Produk",330),("Stok",100),("Minimum",100),("Status",120)])
        def load():
            t.delete(*t.get_children())
            with con() as c:rs=c.execute("select id,barcode,name,stock,min_stock from products where active=1 order by name").fetchall()
            for x in rs:t.insert("","end",iid=str(x["id"]),values=(x["barcode"],x["name"],x["stock"],x["min_stock"],"MENIPIS" if x["stock"]<=x["min_stock"] else "AMAN"))
        def adj():
            i=t.focus()
            if not i:return
            q=simpledialog.askfloat("Stok","+ masuk / - keluar:",parent=self)
            if q is None:return
            with con() as c:
                s=c.execute("select stock from products where id=?",(i,)).fetchone()
                if s["stock"]+q<0:return messagebox.showwarning("Stok","Stok tidak boleh minus.",parent=self)
                c.execute("update products set stock=stock+? where id=?",(q,i));c.execute("insert into stock_movements(product_id,movement_type,quantity,reference,created_at,user_id) values(?,?,?,?,?,?)",(i,"ADJUST",q,"MANUAL",now(),self.user["id"]))
            load()
        ttk.Button(bar,text="PENYESUAIAN STOK",command=adj).pack(side="left");load()
    def p_pembelian(self):
        self.head("Pembelian","Stok masuk dari supplier")
        ttk.Button(self.body,text="＋ PEMBELIAN BARU",command=self.new_purchase).pack(anchor="w",padx=22,pady=4)
        t=self.tree(self.body,[("Invoice",190),("Tanggal",160),("Supplier",230),("Total",140),("Bayar",140)])
        with con() as c:rs=c.execute("select p.invoice_no,p.created_at,coalesce(s.name,''),p.total,p.paid from purchases p left join suppliers s on s.id=p.supplier_id order by p.id desc").fetchall()
        for x in rs:t.insert("","end",values=(x["invoice_no"],x["created_at"],x[2],rup(x["total"]),rup(x["paid"])))
    def new_purchase(self):
        d=tk.Toplevel(self);d.title("Pembelian Baru");d.geometry("820x600");sup=tk.StringVar();paid=tk.DoubleVar();items=[]
        with con() as c:rs=c.execute("select id,name from suppliers where active=1 order by name").fetchall()
        mp={x["name"]:x["id"] for x in rs};top=tk.Frame(d);top.pack(fill="x",padx=15,pady=10);ttk.Combobox(top,textvariable=sup,values=list(mp),state="readonly",width=30).pack(side="left")
        t=self.tree(d,[("Produk",320),("Qty",80),("Harga",130),("Total",150)])
        def add():
            with con() as c:ps=c.execute("select id,name,cost_price from products where active=1 order by name").fetchall()
            n=simpledialog.askstring("Produk","Nama produk:",parent=d);r=next((x for x in ps if x["name"].lower()==(n or "").lower()),None)
            if not r:return
            q=simpledialog.askfloat("Qty","Jumlah:",parent=d,minvalue=.01);p=simpledialog.askfloat("Harga","Harga beli:",parent=d,minvalue=0)
            if q is not None and p is not None:items.append((r["id"],r["name"],q,p));refresh()
        def refresh():
            t.delete(*t.get_children())
            for x in items:t.insert("","end",values=(x[1],x[2],rup(x[3]),rup(x[2]*x[3])))
        def save():
            if not items or not sup.get():return messagebox.showwarning("Pembelian","Supplier dan item wajib diisi.",parent=d)
            z=sum(x[2]*x[3] for x in items);inv="PUR-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            with con() as c:
                c.execute("insert into purchases(invoice_no,created_at,user_id,supplier_id,total,paid) values(?,?,?,?,?,?)",(inv,now(),self.user["id"],mp[sup.get()],z,float(paid.get() or 0)));pid=c.execute("select last_insert_rowid()").fetchone()[0]
                for x in items:c.execute("insert into purchase_items(purchase_id,product_id,quantity,unit_cost,line_total) values(?,?,?,?,?)",(pid,x[0],x[2],x[3],x[2]*x[3]));c.execute("update products set stock=stock+?,cost_price=? where id=?",(x[2],x[3],x[0]))
            d.destroy();self.p_pembelian()
        ttk.Button(top,text="Tambah Item",command=add).pack(side="left",padx=8);tk.Label(top,text="Bayar").pack(side="left");ttk.Entry(top,textvariable=paid,width=14).pack(side="left");ttk.Button(d,text="SIMPAN",command=save).pack(anchor="e",padx=20,pady=12)
    def p_pelanggan(self):self.master_page("Pelanggan","customers")
    def p_supplier(self):self.master_page("Supplier","suppliers")
    def master_page(self,title,table):
        self.head(title,"Master data");bar=tk.Frame(self.body,bg="#eef2f7");bar.pack(fill="x",padx=22);t=self.tree(self.body,[("ID",60),("Nama",300),("Telepon",180),("Alamat",450)])
        def load():
            t.delete(*t.get_children())
            with con() as c:rs=c.execute("select id,name,phone,address from "+table+" where active=1 order by name").fetchall()
            for x in rs:t.insert("","end",values=tuple(x))
        def add():
            d=tk.Toplevel(self);d.title(title);es=[ttk.Entry(d) for _ in range(3)]
            for lab,e in zip(["Nama","Telepon","Alamat"],es):tk.Label(d,text=lab).pack(anchor="w",padx=20);e.pack(fill="x",padx=20,pady=5)
            def save():
                with con() as c:c.execute("insert into "+table+"(name,phone,address) values(?,?,?)",[e.get() for e in es])
                d.destroy();load()
            ttk.Button(d,text="SIMPAN",command=save).pack(pady=15)
        ttk.Button(bar,text="＋ TAMBAH",command=add).pack(side="left");load()
    def p_pengguna(self):
        self.head("Pengguna","Admin/Kasir • reset password aman")
        bar=tk.Frame(self.body,bg="#eef2f7");bar.pack(fill="x",padx=22);t=self.tree(self.body,[("ID",60),("Username",180),("Nama",260),("Role",100),("Status",100)])
        def load():
            t.delete(*t.get_children())
            with con() as c:rs=c.execute("select id,username,name,role,active from users").fetchall()
            for x in rs:t.insert("","end",values=(x["id"],x["username"],x["name"],x["role"],"AKTIF" if x["active"] else "NONAKTIF"))
        def reset():
            i=t.focus()
            if not i:return
            u=t.item(i,"values")[1];p=simpledialog.askstring("Reset Password","Password baru:",show="•",parent=self)
            if p and len(p)>=6:
                b=backup()
                with con() as c:c.execute("update users set password_hash=? where username=?",(ph(p),u))
                messagebox.showinfo("Reset","Berhasil.\nBackup: "+b,parent=self)
        ttk.Button(bar,text="RESET PASSWORD",command=reset).pack(side="left");load()
    def p_laporan(self):
        self.head("Laporan","Penjualan dan ekspor CSV")
        bar=tk.Frame(self.body,bg="#eef2f7");bar.pack(fill="x",padx=22);t=self.tree(self.body,[("Invoice",200),("Tanggal",170),("Kasir",180),("Total",140),("Bayar",140),("Metode",100)])
        with con() as c:rs=c.execute("select s.invoice_no,s.created_at,coalesce(u.name,''),s.total,s.paid,s.payment_method from sales s left join users u on u.id=s.user_id order by s.id desc").fetchall()
        for x in rs:t.insert("","end",values=(x["invoice_no"],x["created_at"],x[2],rup(x["total"]),rup(x["paid"]),x["payment_method"]))
        def exp():
            p=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV","*.csv")])
            if p:
                with open(p,"w",newline="",encoding="utf-8-sig") as f:
                    w=csv.writer(f);w.writerow(["Invoice","Tanggal","Kasir","Total","Bayar","Metode"]);[w.writerow(t.item(i,"values")) for i in t.get_children()]
                messagebox.showinfo("Laporan","CSV tersimpan.",parent=self)
        ttk.Button(bar,text="EXPORT CSV",command=exp).pack(side="left")
    def p_printer_center(self):
        self.head("Printer Center","58mm / 80mm • printer Windows")
        b=tk.Frame(self.body,bg="white");b.pack(fill="x",padx=22,pady=10)
        tk.Label(b,text="Nama printer Windows").pack(anchor="w",padx=20,pady=(18,3));e=ttk.Entry(b);e.insert(0,get("printer_name"));e.pack(fill="x",padx=20,ipady=6)
        tk.Label(b,text="Ukuran struk").pack(anchor="w",padx=20,pady=(12,3));w=ttk.Combobox(b,values=["58mm","80mm"],state="readonly");w.set(get("receipt_width"));w.pack(fill="x",padx=20,ipady=6)
        def save():setv("printer_name",e.get());setv("receipt_width",w.get());messagebox.showinfo("Printer","Tersimpan.",parent=self)
        ttk.Button(b,text="SIMPAN",command=save).pack(anchor="w",padx=20,pady=18)
    def p_pengaturan(self):
        self.head("Pengaturan","Identitas toko dan backup/restore")
        b=tk.Frame(self.body,bg="white");b.pack(fill="x",padx=22,pady=10);es={}
        for k,l in [("store_name","Nama Toko"),("store_address","Alamat"),("store_phone","Telepon"),("receipt_footer","Footer Struk")]:
            tk.Label(b,text=l).pack(anchor="w",padx=20,pady=(10,2));e=ttk.Entry(b);e.insert(0,get(k));e.pack(fill="x",padx=20,ipady=6);es[k]=e
        def save():
            for k,e in es.items():setv(k,e.get())
            messagebox.showinfo("Pengaturan","Tersimpan.",parent=self)
        def bk():messagebox.showinfo("Backup","Backup dibuat:\n"+backup(),parent=self)
        def restore():
            p=filedialog.askopenfilename(filetypes=[("SQLite DB","*.db")])
            if p and messagebox.askyesno("Restore","Backup database saat ini lalu restore?",parent=self):
                b=backup();shutil.copy2(p,DB);messagebox.showinfo("Restore","Selesai. Backup lama:\n"+b,parent=self);self.destroy();self.root.destroy()
        ttk.Button(b,text="SIMPAN",command=save).pack(side="left",padx=20,pady=18);ttk.Button(b,text="BACKUP",command=bk).pack(side="left");ttk.Button(b,text="RESTORE",command=restore).pack(side="left",padx=8)

if __name__=="__main__":init();Login().mainloop()
