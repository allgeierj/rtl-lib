module gray2bin
#(
  parameter int Width = 8
)
(
  input logic [Width-1:0] c0_gray_i,
  output logic [Width-1:0] c0_bin_o
);

if(Width < 1) $error("Width must be >= 1 (got %0d)", Width);

always_comb begin
  c0_bin_o[Width-1] = c0_gray_i[Width-1];
  for(int i = Width-2; i >= 0; i--) begin
    c0_bin_o[i] = c0_bin_o[i+1] ^ c0_gray_i[i];
  end
end

endmodule
