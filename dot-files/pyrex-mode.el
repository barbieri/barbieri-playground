;;;; `Pyrex' mode.

(add-to-list 'auto-mode-alist '("\\.\\(pyx\\|pxd\\)\\'" . pyrex-mode))

(define-derived-mode pyrex-mode python-mode "Pyrex"
  (font-lock-add-keywords
   nil
   `((,(concat "\\<\\(NULL"
	       "\\|c\\(def\\|har\\|typedef\\|import\\)"
	       "\\|e\\(num\\|xtern\\)"
	       "\\|float"
	       "\\|in\\(clude\\|t\\)"
	       "\\|object\\|public\\|struct\\|type\\|union\\|void"
	       "\\)\\>")
      1 font-lock-keyword-face t))))

(defun pyrex-getter-name (name) (concat name "_get"))
(defun pyrex-setter-name (name) (concat name "_set"))

(defun pyrex-getter-and-setter-new (name &optional type)
  "Generate the skeleton implementation for a new getter and setter."
  (interactive "sName: ")
  (insert
   (concat
    "\n"
    "    def " (pyrex-getter-name name) "(self):\n"
    "        return \n\n"
    "    def " (pyrex-setter-name name) "(self, "
    (if (not (eq 'nil type)) (concat type " "))
    "value):\n"
    "        ()\n"
    ))
  )

(defun pyrex-property-new (name &optional type)
  "Generate the code implementation for a new pyrex property."
  (interactive "sName: ")
  (insert
   (concat
    "\n"
    "    property " name ":\n"
    "        def __get__(self):\n"
    "            return self." (pyrex-getter-name name) "()\n\n"
    "        def __set__(self, "
    (if (not (eq 'nil type)) (concat type " "))
    "value):\n"
    "            self." (pyrex-setter-name name) "(value)\n"
    ))
  )

(defun pyrex-property-and-getter-and-setter-new (name &optional type)
  (interactive "sName: ")
  (pyrex-getter-and-setter-new name type)
  (pyrex-property-new name type))

(defun pyrex-property-margs-new (name)
  "Generate the code implementation for a new pyrex multi-argument property.

  It assumes that setter method receives a list of argument and so
  calls it with expanded list of arguments (*args).
  "
  (interactive "sName: ")
  (insert
   (concat
    "\n"
    "property " name ":\n"
    "    def __get__(self):\n"
    "        return self." (pyrex-getter-name name) "()\n\n"
    "    def __set__(self, spec):\n"
    "        self." (pyrex-setter-name name) "(*spec)\n"
    )))

(defun pyrex-property-double-new (name)
  "Generate the code implementation for a new pyrex integer property.

  It check for an integer parameter.
  "
  (interactive "sName: ")
  (pyrex-property-new name "int"))

(defun pyrex-property-and-getter-and-setter-int-new (name)
  (interactive "sName: ")
  (pyrex-property-and-getter-and-setter-new name "int"))

(defun pyrex-property-double-new (name)
  "Generate the code implementation for a new pyrex double property.

  It check for an double parameter.
  "
  (interactive "sName: ")
  (pyrex-property-new name "double"))

(defun pyrex-property-and-getter-and-setter-double-new (name)
  (interactive "sName: ")
  (pyrex-property-and-getter-and-setter-new name "double"))

(defun pyrex-property-str-new (name)
  "Generate the code implementation for a new pyrex string property.

  It check for an char* parameter.
  "
  (interactive "sName: ")
  (pyrex-property-new name "char *"))

(defun pyrex-property-and-getter-and-setter-str-new (name)
  (interactive "sName: ")
  (pyrex-property-and-getter-and-setter-new name "char *"))

