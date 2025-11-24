-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:18 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v7 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
v7:require_server(function() --[[ Line: 12 ]]
    --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (ref 3): v_u_10 ]]
    v_u_8 = require(game.ReplicatedStorage.Server.EnvironmentSetupServer)
    v_u_9 = require(game.ReplicatedStorage.LobbyDecoration.RegisterLobbyDecoration)
    v_u_10 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.Black17EventInfo)
end)
local v11 = {}
local v_u_12 = v_u_2:new():add_set_from_table_list({
    "LobbyTruckCoffee",
    "LobbyTruckGear",
    "LobbyTruckNews",
    "LobbyTruckDance",
    "ParkAutumnFestival"
})
local v_u_13 = v_u_2:new():add_set_from_table_list({ "ParkFoodCart", "SidewalkObjects" })
local v_u_14 = v_u_2:new()
local v_u_15 = v_u_2:new()
v11.setup_environment_decorations = function(_) --[[ Name: setup_environment_decorations ]] --[[ Line: 57 ]]
    --[[ Upvalues: (copy 1): v_u_14, (copy 2): v_u_5, (copy 3): v_u_4, (copy 4): v_u_15, (copy 5): v_u_2 ]]
    local function f_add_decoration_models_root(p16) --[[ Name: add_decoration_models_root ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4 ]]
        if p16 ~= nil then
            for _, v17 in pairs(p16:GetChildren()) do
                for _, v18 in pairs(v17:GetChildren()) do
                    if v_u_14:contains(v18.Name) then
                        v_u_5:errf("duplicate decoration name(%s)", v18.Name)
                    end;
                    v_u_4:is_true(v18.PrimaryPart ~= nil, "decoration(%s) has no PrimaryPart", v18.Name)
                    v_u_14:add(v18.Name, v18)
                end;
            end;
            p16.Parent = nil
        end;
    end;
    f_add_decoration_models_root(game.ServerStorage:FindFirstChild("LobbyDecorationModels"))
    f_add_decoration_models_root(game.Workspace:FindFirstChild("LobbyDecorationModels"))
    local function f_add_decoration_anchor_root(p19) --[[ Name: add_decoration_anchor_root ]] --[[ Line: 78 ]]
        --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_2, (ref 3): v_u_14, (ref 4): v_u_5 ]]
        if p19 ~= nil then
            for _, v20 in pairs(p19:GetChildren()) do
                local l_Name_0 = v20.Name
                local v21
                if v_u_15:contains(l_Name_0) then
                    v21 = v_u_15:get(l_Name_0)
                else
                    v21 = v_u_2:new()
                    v_u_15:add(l_Name_0, v21)
                end;
                for _, v22 in pairs(v20:GetChildren()) do
                    local l_Name_1 = v22.Name
                    if v_u_14:contains(l_Name_1) then
                        v21:add(l_Name_1, v22.CFrame)
                    else
                        v_u_5:errf("model anchor[%s](%s) has no model", l_Name_0, l_Name_1)
                    end;
                end;
            end;
            p19.Parent = nil
        end;
    end;
    f_add_decoration_anchor_root(game.ServerStorage:FindFirstChild("LobbyDecorationAnchors"))
    f_add_decoration_anchor_root(game.Workspace:FindFirstChild("LobbyDecorationAnchors"))
    for v23, v24 in v_u_15:key_itr() do
        if v24:contains(v23) == false then
            v_u_5:errf("decoration group(%s) has no default", v23)
        end;
    end;
end;
local v_u_25 = v_u_1:new()
v11.server_loaded_setup = function(_, p_u_26) --[[ Name: server_loaded_setup ]] --[[ Line: 115 ]]
    --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_13, (copy 3): v_u_5, (copy 4): v_u_2, (copy 5): v_u_15, (copy 6): v_u_6, (copy 7): v_u_12, (copy 8): v_u_14, (copy 9): v_u_1, (copy 10): v_u_3, (ref 11): v_u_9, (copy 12): v_u_25, (ref 13): v_u_8 ]]
    if v_u_10:server_environment_decoration_setup_enabled() == true then
        v_u_13:add_set("MarketplaceTruck")
    end;
    v_u_5:puts("--ServerEnvironmentDecorationSetup:server_loaded_setup--")
    local l_Model_0 = Instance.new("Model")
    l_Model_0.Name = "PlacedLobbyDecorations"
    local v40, v41 = pcall(function() --[[ Line: 125 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_15, (ref 3): v_u_13, (ref 4): v_u_6, (ref 5): v_u_12, (ref 6): v_u_14, (ref 7): v_u_1, (ref 8): v_u_5, (ref 9): v_u_3, (copy 10): l_Model_0 ]]
        local v_u_27 = v_u_2:new()
        local v28 = v_u_15:key_list()
        v28:shuffle()
        for _, v_u_29 in v28:key_itr() do
            local v30 = v_u_15:get(v_u_29)
            local v31 = v30:key_list()
            if not v_u_13:contains(v_u_29) then
                if v_u_6.ServerDecorationUseDefault == true then
                    v31:remove_if(function(p32) --[[ Line: 139 ]]
                        --[[ Upvalues: (copy 1): v_u_29 ]]
                        return p32 ~= v_u_29;
                    end)
                else
                    v31:remove_if(function(p33) --[[ Line: 144 ]]
                        --[[ Upvalues: (copy 1): v_u_27 ]]
                        return v_u_27:contains(p33);
                    end)
                    for _, v34 in v31:key_itr() do
                        if v_u_12:contains(v34) and v_u_14:contains(v34) then
                            v_u_12:remove(v34)
                            v_u_27:add_set(v34)
                            v31 = v_u_1:new({ v34 })
                            break;
                        end;
                    end;
                end;
                if v31:count() > 0 then
                    local l_Model_1 = Instance.new("Model")
                    l_Model_1.Name = v_u_29
                    local v35 = v31:random()
                    local v36 = v_u_14:get(v35):Clone()
                    v36:SetPrimaryPartCFrame(v30:get(v35))
                    v36.Parent = l_Model_1
                    v_u_5:puts("\tServerEnvironmentDecorationSetup(%d) group(%s) using model(%s)", v31:count(), v_u_29, v35)
                    local v37 = v_u_3:get_list_of_children_of_classname(v36, "Sky")
                    if v37:count() > 0 then
                        local v38 = v37:get(1)
                        local v_u_39 = nil
                        v_u_3:ptry(function() --[[ Line: 179 ]]
                            --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_3 ]]
                            v_u_39 = v_u_3:get_list_of_children_of_classname(game.Lighting, "Sky"):get(1)
                        end)
                        if v_u_39 then
                            v_u_39.SkyboxBk = v38.SkyboxBk
                            v_u_39.SkyboxDn = v38.SkyboxDn
                            v_u_39.SkyboxFt = v38.SkyboxFt
                            v_u_39.SkyboxLf = v38.SkyboxLf
                            v_u_39.SkyboxRt = v38.SkyboxRt
                            v_u_39.SkyboxUp = v38.SkyboxUp
                            v_u_5:puts("\tServerEnvironmentDecorationSetup replace sky(%s)", v38:GetFullName())
                        end;
                    end;
                    l_Model_1.Parent = l_Model_0
                else
                    v_u_5:warnf("\tServerEnvironmentDecorationSetup(%d) group(%s) has no model", v31:count(), v_u_29)
                end;
            end;
        end;
    end)
    if v40 ~= true then
        v_u_5:warnf("ServerEnvironmentDecorationSetup:server_loaded_setup failed(%s)", v41)
    end;
    local v_u_42 = v_u_9:get_class_to_name_dict()
    local v46, v47 = pcall(function() --[[ Line: 212 ]]
        --[[ Upvalues: (copy 1): l_Model_0, (copy 2): v_u_42, (ref 3): v_u_25, (ref 4): v_u_3, (ref 5): v_u_5, (copy 6): p_u_26 ]]
        for _, v43 in pairs(l_Model_0:GetChildren()) do
            for _, v44 in pairs(v43:GetChildren()) do
                local l_Name_2 = v44.Name
                if v_u_42:contains(l_Name_2) then
                    v_u_25:push_back(v_u_42:get(l_Name_2):new(v44))
                elseif v_u_3:is_dev_build() then
                    v_u_5:puts("ServerEnvironmentDecorationSetup:setup_environment_decorations() decoration(%s) no handling code", v44.Name)
                end;
            end;
        end;
        for _, v45 in v_u_25:key_itr() do
            v45:on_server_startup(p_u_26)
        end;
    end)
    if not v46 then
        v_u_5:warnf("ServerEnvironmentDecorationSetup:setup_environment_decorations failed to setup decorations: %s", v47)
    end;
    l_Model_0.Parent = v_u_8:get_environment()
end;
return v11;
