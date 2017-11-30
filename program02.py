class ResourceAllocSimulator:
	def __init__(self, resources, claim):
		self.blocked   = set()
		self.available = resources                                       # Total amount of each resource not allocated to any process
		self.claim     = claim                                           # Requirement of process `row` for resource `column`
		self.allocated = list([0] * len(required) for required in claim) # Current allocation to process `row` of resource `column`
	

	def alloc_req(self, pid, request):
		assert(pid not in self.blocked)
		assert(self.allocated[pid] is not None)
		
		# Prima di tutto si controlla se le richieste possono essere soddisfatte
		for resource, requested_amount in enumerate(request):
			# Se le risorse precedentemente allocate più quelle appena richieste superano
			# la quantità dichiarata necessaria dal processo c'è un errore
			if self.allocated[pid][resource] + requested_amount > self.claim[pid][resource]:
				return "Error"
			
			# Se la quantità di risorse richieste supera quelle attualmente disponibili
			# il processo viene bloccato fino a che non verranno liberate quelle risorse
			if requested_amount > self.available[resource]:
				self.blocked.add(pid)
				return "Blocked"
		
		# Se si arriva a questo punto il sistema ha la capacità di assegnare al processo le risorse che richiede
		# Si deve simulare l'allocazione per controllare che il nuovo stato non causerebbe un deadlock
		
		# Si calcola lo stato del sistema dopo l'allocazione
		new_available = self.available[:]
		new_allocated = [alloc_per_proc[:] if alloc_per_proc else None for alloc_per_proc in self.allocated]
		for resource, requested_amount in enumerate(request):
			new_available[resource]      -= requested_amount
			new_allocated[pid][resource] += requested_amount
		
		# Se si verrebbe a causare un deadlock, il processo viene bloccato finchè non ci sono più risorse diponibili
		if not _is_safe_state(self.claim, new_available, new_allocated, self.blocked):
			self.blocked.add(pid)
			return "Blocked"
		
		# if not safe(self.claim, new_allocated, new_available, len(new_available), self.get_ready()):
		# 	self.blocked.add(pid)
		# 	return "Blocked"
		
		# Si allocano le risorse: lo stato simulato diventa l'effettivo stato del sistema
		self.available = new_available
		self.allocated = new_allocated
		return "OK"
	

	def complete(self, pid):
		assert(pid not in self.blocked)
		assert(self.allocated[pid] is not None)
		
		resources_count = len(self.available)
		# Se un processo non ha abbastanza risorse disponibili per terminare, si ritorna False
		if any(self.allocated[pid][res] + self.available[res] < self.claim[pid][res] for res in range(resources_count)):
			return False
		
		# Si recuperano le risorse allocate al processo e si marca come terminato (mettendo None nella allocation matrix)
		self.available = [self.available[res] + self.allocated[pid][res] for res in range(resources_count)]
		self.allocated[pid] = None
		
		# Si controlla se qualche processo bloccato potrebbe adesso terminare
		for blk in set(self.blocked):
			assert(self.allocated[blk] is not None)
			
			if all(self.allocated[blk][res] + self.available[res] >= self.claim[blk][res] for res in range(resources_count)):
				self.blocked.remove(blk)
		return True
	
	
	def get_alive(self):
		return set(pid for pid, alloc_per_proc in enumerate(self.allocated) if alloc_per_proc is not None)
		
	
	def get_ready(self):
		return self.get_alive() - self.get_blocked()
	

	def get_blocked(self):
		return self.blocked
	

	def get_allocated(self):
		return self.allocated


def safe(claim, alloc, available, resources_count, processes):
	currentavail = available[:]
	rest         = set(processes)
	possible = True
	while possible:
		found = None
		for pid in rest:
			if all(claim[pid][res] - alloc[pid][res] <= currentavail[res] for res in range(resources_count)):
				found = pid
				break
		
		if found is not None:
			currentavail = [currentavail[res] + alloc[pid][res] for res in range(resources_count)]
			rest = rest - {found}
		else:
			possible = False
	return rest == set()
	

def _is_safe_state(claim, available, allocated, blocked_procs):
	"""Controlla se lo stato del sistema porterebbe ad un deadlock.
Gli argomenti sono read-only"""
	
	resources_count = len(available)
	# Copy arguments to avoid overwriting caller values
	available     = available[:]
	
	# Get list of ready processes (terminated processes have None in the allocation matrix)
	processes   = set(pid for pid, alloc_per_proc in enumerate(allocated) if alloc_per_proc is not None)
	ready_procs = processes - blocked_procs
	
	# Si simula una esecuzione completa di tutti i processi
	# `ready_procs` rappresenta i processi che non hanno ancora terminato la loro esecuzione
	# Ad ogni ciclo si cerca un processo che, data l'attuale allocazione di risorse, è capace di terminare
	# Se lo si trova, si simula il completamento della sua esecuzione
	# In pratica vuol dire che si rilasciano le risorse che ha attualmente allocate e il processo viene tolto
	# dalla lista di quelli in esecuzione
	# A quel punto il ciclo ricomincia e si cerca un altro processo, con la differenza che adesso le risorse disponibili
	# contano anche quelle del processo appena termianto
	# Quindi potenzialmente un processo che prima non aveva abbastanza risorse per terminare adesso ne ha abbastanza
	# Questa operazione si ripete finchè la lista dei processi in esecuzione non rimane vuota
	# Se ciò succede, significa che nello stato attuale il sistema è capace di trovare una sequenza di
	# esecuzione/allocazione capace di portare a termine tutti i processi
	# Se invece ad un certo punto non viene trovato nessun processo capace di terminare, vuol dire che l'allocazione
	# di risorse con cui ha iniziato la simulazione ad un certo punto causerà lo stallo del sistema
	while ready_procs:
		
		# Si parte con l'assunzione che ci si trova in uno stato di stallo. Se viene trovato un processo capace
		# di terminare, allora si imposta `deadlock` a False
		deadlock = True
		
		# Si cerca un processo che, data l'attuale allocazione di risorse, è capace di terminare
		for pid in ready_procs:
			# Un processo è capace di terminare se, per ogni risorsa, le risorse che ha più quelle che
			# potrebbe avere sono almeno tante quante quelle che effettivamente gli servono
			if all(allocated[pid][res] + available[res] >= claim[pid][res] for res in range(resources_count)):
				
				# Se è stato trovato un processo capace di terminare si simula il completamento della sua esecuzione
				# Si rilasciano le risorse assegnategli e lo si rimuove dalla lista dei processi in esecuzione
				available = [available[res] + allocated[pid][res] for res in range(resources_count)]
				ready_procs.remove(pid)
				
				# Bisogna ricominciare dall'inizio del while. Si imposta `deadlock` a False per evitare il return
				# e si esce dal for tramite un break
				deadlock = False
				break
		
		if deadlock:
			return False
	
	# Se si arriva a questo punto allora non è mai stato rilevato un deadlock, e la lista dei processi da eseguire
	# è rimasta vuota (causando la fine del while). Quindi lo stato iniziale della simulazione è sicuro
	return True
