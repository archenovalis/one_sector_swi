local ffi = require("ffi")
local C = ffi.C

local ModLua = {}
One_Sector = {}

function ModLua.init()
  One_Sector.playerId = ConvertStringTo64Bit(tostring(C.GetPlayerID()))
  RegisterEvent("os.getDemandProduction", One_Sector.getDemandProduction)
end

function One_Sector.getDemandProduction()
  local object = GetNPCBlackboard(One_Sector.playerId, "$gajMaintenanceData")
  local returnData = {}
  returnData.products = {}
  returnData.resources = {}
  local queueDuration = 0
  for _, prodData in ipairs(object.products) do
    queueDuration = queueDuration + prodData.cycle
  end

  -- add products
  for _, prodData in ipairs(object.products) do
    local prodWare = prodData.ware
    if returnData.products[prodWare] then
      returnData.products[prodWare] = returnData.products[prodWare] +
        Helper.round(prodData.amount * 3600 / queueDuration)
    else
      returnData.products[prodWare] = Helper.round(prodData.amount * 3600 / queueDuration)
    end

    -- add resources
    for _, resData in ipairs(prodData.resources) do
      local resWare = resData.ware
      if returnData.resources[resWare] then
        returnData.resources[resWare] = returnData.resources[resWare] +
          Helper.round(resData.amount * 3600 / queueDuration)
      else
        returnData.resources[resWare] = Helper.round(resData.amount * 3600 / queueDuration)
      end
    end
  end
  AddUITriggeredEvent("OneSector", "setDemandProduction", returnData)
end

return ModLua
