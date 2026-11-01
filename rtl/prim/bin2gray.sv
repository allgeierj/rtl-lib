module bin2gray
#(
  parameter int Width = 8
)
(
  input logic [Width-1:0] c0_bin_i,
  output logic [Width-1:0] c0_gray_o
);

if(Width < 1) $error("Width must be >= 1 (got %0d)", Width);

always_comb begin
  c0_gray_o = c0_bin_i ^ (c0_bin_i >> 1);
end

endmodule
