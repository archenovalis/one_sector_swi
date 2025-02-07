local ffi = require("ffi")
local C = ffi.C
--ffi.cdef [[
--	uint32_t GetNumWares(const char* tags, bool research, const char* licenceownerid, const char* exclusiontags);
--  uint32_t GetWares(const char** result, uint32_t resultlen, const char* tags, bool research, const char* licenceownerid, const char* exclusiontags);
--]]

local ModLua = {}
One_Sector = {}
Macros = {}

function ModLua.init()
  One_Sector.playerId = ConvertStringTo64Bit(tostring(C.GetPlayerID()))
  RegisterEvent("oneSector.assessProductionDemandOutput", One_Sector.assessProductionDemandOutput)
end

-- todo change to looping through receiving multiple objects. receive [$objects, $faction], return {$}
function One_Sector.assessProductionDemandOutput()
  local output = {}
  for _, entry in ipairs(GetLibrary("moduletypes_production")) do
    local object = GetLibraryEntry("moduletypes_production", entry.id)
    output[object] = {}
    output[object]['entry'] = entry
    output[object]['macro'] = entry.macro
    output[object]['idmacro'] = entry.id.macro

    local queueDuration = 0
    for _, prodData in ipairs(object.products) do
      queueDuration = queueDuration + prodData.cycle
    end

    local products = {}
    local demands = {}
    -- add products
    for _, prodData in ipairs(object.products) do
      local prodWare = prodData.ware
      if products[prodWare] then
        products[prodWare] = output.products[prodWare] +
            Helper.round(prodData.amount * 3600 / queueDuration)
      else
        products[prodWare] = Helper.round(prodData.amount * 3600 / queueDuration)
      end
      -- add demands
      for _, resData in ipairs(prodData.resources) do
        local resWare = resData.ware
        if demands[resWare] then
          demands[resWare] = demands[resWare] +
              Helper.round(resData.amount * 3600 / queueDuration)
        else
          demands[resWare] = Helper.round(resData.amount * 3600 / queueDuration)
        end
      end
    end
    output[object]['products'] = products
    output[object]['demands'] = demands
  end
  AddUITriggeredEvent("OneSector", "setProductionDemandOutput", output)
end

--[[ function One_Sector.getWares()
  local numwares = C.GetNumWares("module", false, nil, nil)
  local wares = ffi.new("const char*[?]", numwares)
  numwares = C.GetWares(wares, numwares, "module", false, nil, nil)
  for i = 0, numwares - 1 do
    local locware = ffi.string(wares[i])
    local macro = GetWareData(locware, "component")
    local librarytype
    if macro ~= "" then
      librarytype = GetMacroData(macro, "infolibrary")
    end
    if librarytype == "moduletypes_production" then
      Macros[macro] = locware
    end
  end
end ]]

return ModLua
