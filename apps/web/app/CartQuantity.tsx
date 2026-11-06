"use client";
import { useEffect, useRef, useState } from "react";
export default function CartQuantity({
  item,
  disabled,
  update,
  remove,
}: {
  item: { product: string; variant: string; quantity: number };
  disabled: boolean;
  update: (quantity: number) => void;
  remove: () => void;
}) {
  const [quantity, setQuantity] = useState(String(item.quantity));
  const editing = useRef(false);
  useEffect(() => {
    setQuantity(current => {
      const latest = String(item.quantity);
      if (!editing.current || current === latest) {
        editing.current = false;
        return latest;
      }
      return current;
    });
  }, [item.quantity]);
  const value = Number(quantity);
  const valid = Number.isInteger(value) && value >= 1 && value <= 10;
  return (
    <div className="cart-quantity">
      <label>
        Quantity
        <input
          aria-label={"Quantity " + item.product + " " + item.variant}
          type="number"
          min="1"
          max="10"
          value={quantity}
          disabled={disabled}
          onChange={(e) => { editing.current = true; setQuantity(e.target.value); }}
        />
      </label>
      <button
        disabled={disabled || !valid || value === item.quantity}
        onClick={() => { editing.current = false; update(value); }}
      >
        Update quantity
      </button>
      <button disabled={disabled} onClick={remove}>
        Remove item
      </button>
      {!valid && <p role="alert">Choose a quantity from 1 to 10.</p>}
    </div>
  );
}
