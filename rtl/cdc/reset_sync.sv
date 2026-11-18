// Active-high reset synchroniser: asserts asynchronously, deasserts Stages clk edges after async_rst_i falls.
// Powers up asserted. No cycle prefixes, since the two edges have different latencies.
module reset_sync
#(
  parameter int Stages = 2,
  localparam int Latency = Stages
)
(
  input logic clk,
  input logic async_rst_i,
  output logic rst_o
);

if(Stages < 2) $error("Stages must be >= 2 (got %0d)", Stages);

(* ASYNC_REG = "TRUE" *) logic [Stages-1:0] sync_reg = '1;

assign rst_o = sync_reg[Stages-1];

always_ff @(posedge clk or posedge async_rst_i) begin
  if(async_rst_i) begin
    sync_reg <= '1;
  end 
  else begin
    sync_reg[0] <= 1'b0;
    for(int i = 0; i < Stages-1; i++) begin
      sync_reg[i+1] <= sync_reg[i];
    end
  end
end

endmodule
