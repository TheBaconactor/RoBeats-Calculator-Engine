-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:09 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ForwardCompatSerialization)
local v_u_3 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
local function _() --[[ Name: manual_run_forward_compat_integration_tests ]] --[[ Line: 48 ]]
    print(game:GetService("DataStoreService"):GetDataStore("EditorGameCustomMapAndSavedMapInfo"):GetAsync("@Srobeats_dev3@1941@2"))
    local v4 = game:GetService("DataStoreService"):GetDataStore("EditorGameCustomMapAndSavedMapInfo")
    local v5 = v4:GetAsync("@Srobeats_dev3@1941@2")
    v5.SavedMapInfo.TestCompat1 = "TestCompat1-Value"
    v4:SetAsync("@Srobeats_dev3@1941@2", v5)
    warn("Test Write Operation Done")
    print(game:GetService("DataStoreService"):GetDataStore("EditorGamePublishedMapList"):GetAsync("@SGlobalMapList"))
    local v6 = game:GetService("DataStoreService"):GetDataStore("EditorGamePublishedMapList")
    local v7 = v6:GetAsync("@SGlobalMapList")
    v7[1].TestCompat1 = "TestCompat1-Value"
    v6:SetAsync("@SGlobalMapList", v7)
    warn("Test Write Operation Done")
    print(game:GetService("DataStoreService"):GetDataStore("EditorGameCreatorData"):GetAsync("@Secd_4631531021"))
    local v8 = game:GetService("DataStoreService"):GetDataStore("EditorGameCreatorData")
    local v9 = v8:GetAsync("@Secd_4631531021")
    v9.TestCompat1 = "TestCompat1-Value"
    v8:SetAsync("@Secd_4631531021", v9)
    warn("Test Write Operation Done")
    print(game:GetService("DataStoreService"):GetDataStore("EditorGamePublishedMapList"):GetAsync("@SGlobalMapList"))
    local v10 = game:GetService("DataStoreService"):GetDataStore("EditorGamePublishedMapList")
    local v11 = v10:GetAsync("@SGlobalMapList")
    v11[2].SourceSongKey = 2090
    v11[2].CustomMapName = "TestInvalidSongKeyName"
    v10:SetAsync("@SGlobalMapList", v11)
    warn("Test Write Operation Done")
    print(game:GetService("DataStoreService"):GetDataStore("EditorGamePlayerRecentSavedMapInfo"):GetAsync("@Spr_4631531021"))
    local v12 = game:GetService("DataStoreService"):GetDataStore("EditorGamePlayerRecentSavedMapInfo")
    local v13 = v12:GetAsync("@Spr_4631531021")
    v13[3].SourceSongKey = 2090
    v13[3].CustomMapName = "TestInvalidSongKeyName"
    v12:SetAsync("@Spr_4631531021", v13)
    warn("Test Write Operation Done")
end;
return {
    ["run_editor_export_data_forward_compat_tests"] = function(_) --[[ Name: run_editor_export_data_forward_compat_tests ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1 ]]
        local v14 = v_u_3.CreatorData:new()
        v14:set_creator_name("TestCreator1")
        v14:set_creator_rbxid(12345)
        v14:set_received_like_count(69)
        local v15 = v14:to_table()
        local v16 = v14:to_table()
        v16.ForwardCompatTest1 = "TestValue1"
        v16.ForwardCompatTest2 = { "TestValue2", "TestValue3" }
        local v17 = v_u_3.CreatorData:from_datastore_forward_compat_table(v16):to_table()
        v_u_2:is_true(v17.CreatorName == v15.CreatorName)
        v_u_2:is_true(v17.ForwardCompatTest1 == v16.ForwardCompatTest1)
        v_u_2:is_true(v17.ForwardCompatTest2[1] == v16.ForwardCompatTest2[1])
        v_u_2:is_true(v17.ForwardCompatTest2[2] == v16.ForwardCompatTest2[2])
        local v18 = v_u_3.SavedMapInfo:new()
        local v19 = v18:to_table()
        local v20 = v18:to_table()
        v20.ForwardCompatTest1 = "TestValue1"
        v20.ForwardCompatTest2 = { "TestValue2", "TestValue3" }
        local v21 = v_u_3.CreatorData:from_datastore_forward_compat_table(v20):to_table()
        v_u_2:is_true(v21.SourceSongKey == v19.SourceSongKey)
        v_u_2:is_true(v21.ForwardCompatTest1 == v20.ForwardCompatTest1)
        v_u_2:is_true(v21.ForwardCompatTest2[1] == v20.ForwardCompatTest2[1])
        v_u_2:is_true(v21.ForwardCompatTest2[2] == v20.ForwardCompatTest2[2])
        v_u_1:puts("EditorGameDataTests:run_editor_export_data_forward_compat_tests completed successfully")
    end
};
