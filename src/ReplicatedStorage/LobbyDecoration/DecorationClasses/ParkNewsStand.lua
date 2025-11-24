-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:11 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.Override)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.WebNPCAnchors)
local v_u_3 = require(game.ReplicatedStorage.LobbyDecoration.DecorationClasses.LobbyDecorationBase)
local v_u_4 = require(game.ReplicatedStorage.LobbyDecoration.LobbyDecorationUtil)
local v5 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_8 = nil
v5:require_client(function() --[[ Line: 12 ]]
    --[[ Upvalues: (ref 1): v_u_8 ]]
    v_u_8 = require(game.ReplicatedStorage.Lobby.Menus.NewsUI)
end)
return {
    ["get_decoration_name"] = function(_) --[[ Name: get_decoration_name ]] --[[ Line: 18 ]]
        return "ParkNewsStand";
    end,
    ["new"] = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_2, (copy 5): v_u_7, (copy 6): v_u_6, (ref 7): v_u_8 ]]
        local v10 = v_u_3:new()
        v_u_1:get_base_fn(v10, "on_client_startup")
        v10.on_client_startup = function(_, p_u_11) --[[ Name: on_client_startup ]] --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_9, (ref 3): v_u_2, (ref 4): v_u_7, (ref 5): v_u_6, (ref 6): v_u_8 ]]
            v_u_4:register_webnpc_anchors_on_obj(p_u_11, p_u_9)
            local function _(p_u_12) --[[ Name: apply_song_icon_to_decal ]] --[[ Line: 27 ]]
                --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_2, (ref 3): v_u_7, (ref 4): v_u_6 ]]
                p_u_11._shop_local_protocol:request_shop_info_cached(function(p_u_13) --[[ Line: 28 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7, (ref 3): v_u_6, (copy 4): p_u_12 ]]
                    v_u_2:ptry(function() --[[ Line: 29 ]]
                        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_7, (ref 3): v_u_6, (ref 4): p_u_12 ]]
                        local l_AvailableItems_0 = p_u_13.AvailableItems
                        local v14 = v_u_7:new()
                        for v15 = 1, #l_AvailableItems_0 do
                            local v16 = l_AvailableItems_0[v15]
                            if v16.SaleComboKey == nil then
                                v14:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v16.SongKey))
                            end;
                        end;
                        if v14:count() > 0 then
                            p_u_12.Texture = v14:random()
                        end;
                    end)
                end)
            end;
            local function _(p_u_17) --[[ Name: apply_news_banner_to_decal ]] --[[ Line: 46 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_7 ]]
                v_u_8:get_cached_news_data(function(p18) --[[ Line: 47 ]]
                    --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_17 ]]
                    local v19 = v_u_7:new()
                    for v20 = 1, #p18 do
                        local l_ImageAssetId_0 = p18[v20].ImageAssetId
                        if l_ImageAssetId_0 ~= nil and #l_ImageAssetId_0 > 0 then
                            v19:push_back(l_ImageAssetId_0)
                        end;
                    end;
                    if v19:count() > 0 then
                        p_u_17.Texture = v19:random()
                    end;
                end)
            end;
            v_u_2:ptry(function() --[[ Line: 62 ]]
                --[[ Upvalues: (ref 1): p_u_9, (copy 2): p_u_11, (ref 3): v_u_2, (ref 4): v_u_7, (ref 5): v_u_6, (ref 6): v_u_8 ]]
                local l_Decal_0 = p_u_9.IntDecoration.ScreenSquare1.Decal
                p_u_11._shop_local_protocol:request_shop_info_cached(function(p_u_21) --[[ Line: 28 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7, (ref 3): v_u_6, (copy 4): l_Decal_0 ]]
                    v_u_2:ptry(function() --[[ Line: 29 ]]
                        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_7, (ref 3): v_u_6, (ref 4): l_Decal_0 ]]
                        local l_AvailableItems_1 = p_u_21.AvailableItems
                        local v22 = v_u_7:new()
                        for v23 = 1, #l_AvailableItems_1 do
                            local v24 = l_AvailableItems_1[v23]
                            if v24.SaleComboKey == nil then
                                v22:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v24.SongKey))
                            end;
                        end;
                        if v22:count() > 0 then
                            l_Decal_0.Texture = v22:random()
                        end;
                    end)
                end)
                local l_Decal_1 = p_u_9.IntDecoration.ScreenSquare2.Decal
                p_u_11._shop_local_protocol:request_shop_info_cached(function(p_u_25) --[[ Line: 28 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7, (ref 3): v_u_6, (copy 4): l_Decal_1 ]]
                    v_u_2:ptry(function() --[[ Line: 29 ]]
                        --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_7, (ref 3): v_u_6, (ref 4): l_Decal_1 ]]
                        local l_AvailableItems_2 = p_u_25.AvailableItems
                        local v26 = v_u_7:new()
                        for v27 = 1, #l_AvailableItems_2 do
                            local v28 = l_AvailableItems_2[v27]
                            if v28.SaleComboKey == nil then
                                v26:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v28.SongKey))
                            end;
                        end;
                        if v26:count() > 0 then
                            l_Decal_1.Texture = v26:random()
                        end;
                    end)
                end)
                local l_Decal_2 = p_u_9.IntDecoration.ScreenSquare3.Decal
                p_u_11._shop_local_protocol:request_shop_info_cached(function(p_u_29) --[[ Line: 28 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7, (ref 3): v_u_6, (copy 4): l_Decal_2 ]]
                    v_u_2:ptry(function() --[[ Line: 29 ]]
                        --[[ Upvalues: (copy 1): p_u_29, (ref 2): v_u_7, (ref 3): v_u_6, (ref 4): l_Decal_2 ]]
                        local l_AvailableItems_3 = p_u_29.AvailableItems
                        local v30 = v_u_7:new()
                        for v31 = 1, #l_AvailableItems_3 do
                            local v32 = l_AvailableItems_3[v31]
                            if v32.SaleComboKey == nil then
                                v30:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v32.SongKey))
                            end;
                        end;
                        if v30:count() > 0 then
                            l_Decal_2.Texture = v30:random()
                        end;
                    end)
                end)
                local l_Decal_3 = p_u_9.IntDecoration.ScreenSquare4.Decal
                p_u_11._shop_local_protocol:request_shop_info_cached(function(p_u_33) --[[ Line: 28 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7, (ref 3): v_u_6, (copy 4): l_Decal_3 ]]
                    v_u_2:ptry(function() --[[ Line: 29 ]]
                        --[[ Upvalues: (copy 1): p_u_33, (ref 2): v_u_7, (ref 3): v_u_6, (ref 4): l_Decal_3 ]]
                        local l_AvailableItems_4 = p_u_33.AvailableItems
                        local v34 = v_u_7:new()
                        for v35 = 1, #l_AvailableItems_4 do
                            local v36 = l_AvailableItems_4[v35]
                            if v36.SaleComboKey == nil then
                                v34:push_back(v_u_6:singleton():get_coverimage_assetid_for_key(v36.SongKey))
                            end;
                        end;
                        if v34:count() > 0 then
                            l_Decal_3.Texture = v34:random()
                        end;
                    end)
                end)
                local l_Decal_4 = p_u_9.IntDecoration.DisplayScreen.Decal
                v_u_8:get_cached_news_data(function(p37) --[[ Line: 47 ]]
                    --[[ Upvalues: (ref 1): v_u_7, (copy 2): l_Decal_4 ]]
                    local v38 = v_u_7:new()
                    for v39 = 1, #p37 do
                        local l_ImageAssetId_1 = p37[v39].ImageAssetId
                        if l_ImageAssetId_1 ~= nil and #l_ImageAssetId_1 > 0 then
                            v38:push_back(l_ImageAssetId_1)
                        end;
                    end;
                    if v38:count() > 0 then
                        l_Decal_4.Texture = v38:random()
                    end;
                end)
            end)
        end;
        return v10;
    end
};
