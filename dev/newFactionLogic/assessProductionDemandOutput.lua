local ffi = require("ffi")
local C = ffi.C

local ModLua = {}
One_Sector = {}

function ModLua.init()
  One_Sector.playerId = ConvertStringTo64Bit(tostring(C.GetPlayerID()))
  RegisterEvent("oneSector.assessProductionDemandOutput", One_Sector.assessProductionDemandOutput)
end

-- todo change to looping through receiving multiple objects. receive [$objects, $faction], return {$}
function One_Sector.assessProductionDemandOutput()
  local input = GetNPCBlackboard(One_Sector.playerId, "$assessProductionDemandOutput")
  local objects = input.objects
  local output = {}
  output.faction = input.faction
  output.products = {}
  output.resources = {}
  local queueDuration = 0
  for _, prodData in ipairs(objects.products) do
    queueDuration = queueDuration + prodData.cycle
  end

  -- add products
  for _, prodData in ipairs(objects.products) do
    local prodWare = prodData.ware
    if output.products[prodWare] then
      output.products[prodWare] = output.products[prodWare] +
        Helper.round(prodData.amount * 3600 / queueDuration)
    else
      output.products[prodWare] = Helper.round(prodData.amount * 3600 / queueDuration)
    end

    -- add resources
    for _, resData in ipairs(prodData.resources) do
      local resWare = resData.ware
      if output.resources[resWare] then
        output.resources[resWare] = output.resources[resWare] +
          Helper.round(resData.amount * 3600 / queueDuration)
      else
        output.resources[resWare] = Helper.round(resData.amount * 3600 / queueDuration)
      end
    end
  end

  AddUITriggeredEvent("OneSector", "setProductionDemandOutput", output)
end


return ModLua
