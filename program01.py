import threading

class Prenotazioni:
	def __init__(self, max_requests):
		self.semaphore_semaphores_queues = threading.BoundedSemaphore(1)
		self.semaphores_queues = {"N": threading.BoundedSemaphore(1),
		                          "C": threading.BoundedSemaphore(1),
		                          "M": threading.BoundedSemaphore(1)}
		self.semaphore_request = threading.BoundedSemaphore(max_requests)
		self.queues_sizes = {"N": 0, "C": 0, "M": 0}
	
	
	def gestisci_prenotazioni(self, server, info, scrivi_prenotazione):
		# Protegge l'accesso al dizionario dei semafori dei singoli server
		# Questo è necessario perchè se per esempio arrivano due richieste N e C, può succedere che
		# N locka semaphores_queues[N] (quindi il proxy dovrebbe soddisfare tutte le richieste di N prima di
		# cominciare con C) ma, prima che sia in grado di arrivare al pezzo di codice dove blocca gli
		# altri server, C locka semaphores_queues[C], cioè N non riesce a bloccare C in tempo
		# Usando questo semaforo si serializza l'accesso al gruppo di semafori che decide quali
		# server hanno il diritto di usare il proxy
		with self.semaphore_semaphores_queues:
			
			# Questi semafori svolgono due funzioni: evitano race condition e fanno rispettare il turno ai server
			# Mentre il proxy gestisce le richieste di un server X, il semaforo evita race condition
			# quando due richieste da X vogliono modificare il contatore di richieste
			# Inoltre, nel caso in cui semaphores_queues[X] sia stato lockato da una richiesta che non veniva da X,
			# fa si che X venga bloccato finchè le richieste dall'altro server non sono state tutte soddisfatte
			# (il che causa il rilascio di semaphores_queues[X] dalla seconda parte del codice)
			with self.semaphores_queues[server]:
				
				# Si contano quante richieste per ogni server stanno aspettando di essere servite
				# Per come è progettato il codice, solo un contatore alla volta potrà essere maggiore di 0
				self.queues_sizes[server] += 1
				
				# Se la richiesta da un server X è la prima in arrivo, si lockano i semafori
				# relativi a tutti i server tranne X.
				# In questo modo, quando l'attuale thread rilascia semaphore_semaphores_queues (e quindi
				# anche semaphore_queues[X]), altre richieste provenienti da X potranno lockare semaphore_queues[X]
				# ed incrementare il conto della coda senza causare race conditions, mentre richieste provenienti
				# da altri server dovranno aspettare che il semaphore_queues[altro] sia rilasciato dalla seconda parte
				# del codice
				if self.queues_sizes[server] == 1:

					# Se la richiesta non viene da N, si bloccano tutte le richieste da N
					if server != "N":
						self.semaphores_queues["N"].acquire()
					
					# Se la richiesta non viene da C, si bloccano tutte le richieste da C
					if server != "C":
						self.semaphores_queues["C"].acquire()
					
					# Se la richiesta non viene da M, si bloccano tutte le richieste da M
					if server != "M":
						self.semaphores_queues["M"].acquire()
		
		# Si fanno passare al più max_requests contemporaneamente
		with self.semaphore_request:
			scrivi_prenotazione(info)
		
		# Si locka semaphores_queues[X] per evitare race condition nell'accesso del contatore della coda
		with self.semaphores_queues[server]:
			
			# Decrementiamo il contatore di richieste in coda per segnalare che una richiesta è stata soddisfatta
			self.queues_sizes[server] -= 1
			
			# Se tutte le richieste provenienti dal server X sono state soddisfatte, segnaliamo i semafori relativi
			# agli altri server che possono proseguire l'esecuzione
			if self.queues_sizes[server] == 0:
				
				# Se la richiesta non veniva da N, si segnala che le richieste da N possono proseguire
				if server != "N":
					self.semaphores_queues["N"].release()
				
				# Se la richiesta non veniva da C, si segnala che le richieste da C possono proseguire
				if server != "C":
					self.semaphores_queues["C"].release()
				
				# Se la richiesta non veniva da M, si segnala che le richieste da M possono proseguire
				if server != "M":
					self.semaphores_queues["M"].release()
		
