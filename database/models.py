from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, \
                       func, ForeignKey, UniqueConstraint

from database.base import Base


class Address(Base):
    __tablename__ = "addresses"

    address = Column(String(70), primary_key=True)
    order_id = Column(String(50), nullable=False, unique=True)
    dt_created = Column(DateTime(timezone=True), server_default=func.now(),
                        nullable=False)
    priv_key = Column(String(328), nullable=False)

    def __repr__(self):
        return f"<Address {self.address}>"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    dt_created = Column(DateTime(timezone=True), server_default=func.now(),
                        nullable=False)
    txid = Column(String(80), nullable=False)
    vout = Column(Integer, nullable=False)
    amount = Column(Numeric, nullable=False)
    is_cb_active = Column(Boolean, server_default="TRUE", nullable=False,
                          index=True)
    address = Column(String(70), ForeignKey("addresses.address"),
                     nullable=False, index=True)
    order_id = Column(String(50), nullable=False)
    forward_txid = Column(String(80))

    UniqueConstraint(txid, address)

    def __repr__(self):
        return f"<Payment {self.id}>"
